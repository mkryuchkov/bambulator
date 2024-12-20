#!/usr/bin/env python

import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bambu_client import BambuClient

from handlers import dp

logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format="%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d → %(funcName)s()] %(message)s")
logger = logging.getLogger(__name__)

if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
HOSTNAME = os.getenv('HOSTNAME')
ACCESS_CODE = os.getenv('ACCESS_CODE')
SERIAL = os.getenv('SERIAL')
CHAT_ID = int(os.getenv('CHAT_ID'))


async def main() -> None:
    dp["chat_id"] = CHAT_ID
    bambu_client = BambuClient(HOSTNAME, ACCESS_CODE, SERIAL)
    dp["bambu"] = bambu_client

    bot = Bot(token=TOKEN, default=DefaultBotProperties(
        parse_mode=ParseMode.MARKDOWN_V2))

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        logger.info("Starting")
        asyncio.run(main())
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Stopped")
