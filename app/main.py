import asyncio
import logging
import threading
import uvicorn
import hindsight_client
from bot import create_bot_app
from web import app as web_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def run_web():
    uvicorn.run(web_app, host="0.0.0.0", port=3000, log_level="info")


async def run_bot():
    await hindsight_client.ensure_bank()
    logger.info("Hindsight bank ready")

    bot_app = create_bot_app()
    async with bot_app:
        await bot_app.start()
        logger.info("Telegram bot started")
        await bot_app.updater.start_polling()

        # Keep running
        stop_event = asyncio.Event()
        await stop_event.wait()


def main():
    # Start web dashboard in a separate thread
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    logger.info("Dashboard running on port 3000")

    # Run telegram bot in main thread
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
