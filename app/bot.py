import os
import io
import logging
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import hindsight_client

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Du bist der digitale Zwilling des Users. Du kennst ihn besser als jeder andere.
Du sprichst wie er, denkst wie er, und triffst Entscheidungen wie er.
Du bist direkt, ehrlich und authentisch - kein typischer KI-Assistent.

Wenn dir Erinnerungen bereitgestellt werden, nutze sie um wie der User zu antworten.
Wenn du etwas nicht weisst, sag es ehrlich.
Antworte immer auf Deutsch, es sei denn der User schreibt auf Englisch."""


def is_diary_entry(text: str) -> bool:
    diary_indicators = [
        "heute habe ich", "ich habe heute", "ich hab", "ich war",
        "gerade eben", "mir ist aufgefallen", "ich denke dass",
        "ich habe mich entschieden", "mein tag", "ich fuehle",
        "ich finde dass", "ich glaube", "das war", "ich bin",
        "hab gerade", "bin gerade", "war heute", "musste heute",
        "wollte noch sagen", "mir ging", "ich mag", "ich hasse",
        "wichtig fuer mich", "ich plane", "mein plan", "ich will",
        "ich moechte", "ich muss", "ich sollte",
    ]
    lower = text.lower()
    if any(indicator in lower for indicator in diary_indicators):
        return True
    if not text.endswith("?") and len(text) > 50:
        return True
    return False


async def transcribe_voice(voice_bytes: bytes) -> str:
    audio_file = io.BytesIO(voice_bytes)
    audio_file.name = "voice.ogg"
    transcript = await openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="de",
    )
    return transcript.text


async def get_twin_response(query: str) -> str:
    memories = await hindsight_client.recall(query, limit=8)

    memory_context = ""
    if memories:
        items = memories if isinstance(memories, list) else memories.get("results", memories.get("memories", []))
        for m in items:
            content = m.get("content", m.get("text", str(m)))
            memory_context += f"- {content}\n"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    if memory_context:
        messages.append({
            "role": "system",
            "content": f"Relevante Erinnerungen an den User:\n{memory_context}"
        })

    messages.append({"role": "user", "content": query})

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
        max_tokens=1000,
    )
    return response.choices[0].message.content


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey! Ich bin dein digitaler Zwilling.\n\n"
        "Schick mir Sprachnachrichten oder Text:\n"
        "- Erzaehl mir von deinem Tag (wird gespeichert)\n"
        "- Stell mir eine Frage (ich antworte wie du)\n\n"
        "/reflect - Muster aus Erinnerungen ableiten\n"
        "/status - Systemstatus anzeigen"
    )


async def cmd_reflect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Reflektiere ueber deine Erinnerungen...")
    try:
        result = await hindsight_client.reflect()
        await update.message.reply_text(f"Reflection abgeschlossen:\n{result}")
    except Exception as e:
        await update.message.reply_text(f"Fehler bei Reflection: {e}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    healthy = await hindsight_client.health_check()
    status = "online" if healthy else "offline"
    await update.message.reply_text(f"Hindsight: {status}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice or update.message.audio
    if not voice:
        return

    file = await context.bot.get_file(voice.file_id)
    voice_data = await file.download_as_bytearray()

    await update.message.reply_text("Transkribiere...")
    text = await transcribe_voice(bytes(voice_data))

    await process_message(update, text)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return
    await process_message(update, text)


async def process_message(update: Update, text: str):
    if is_diary_entry(text):
        try:
            await hindsight_client.retain(text, metadata={
                "type": "diary",
                "source": "telegram",
            })
            await update.message.reply_text(f"Gespeichert.\n\n\"{text[:200]}{'...' if len(text) > 200 else ''}\"")
        except Exception as e:
            logger.error("Retain failed: %s", e)
            await update.message.reply_text(f"Fehler beim Speichern: {e}")
    else:
        try:
            response = await get_twin_response(text)
            await update.message.reply_text(response)
        except Exception as e:
            logger.error("Response failed: %s", e)
            await update.message.reply_text(f"Fehler: {e}")


def create_bot_app() -> Application:
    app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reflect", cmd_reflect))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    return app
