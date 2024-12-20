#!/usr/bin/env python
"""
Telgram bot message handlers.
"""

import asyncio
import logging
import jsonpickle
from typing import Any, Awaitable, Callable, Dict, Optional
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.methods import SetMyCommands
from aiogram.types import Message, BotCommand, BufferedInputFile, BotCommandScopeChat

from bambu_client import BambuClient

logger = logging.getLogger(__name__)

dp = Dispatcher()

# todo: handle printer offline state
# todo: send messages on printer events
# todo: reconnect command
# todo: nice status message
# todo: gif from image buffer


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    `/start` command
    """
    # todo: authorization
    await message.answer(f"Hello, {message.from_user.full_name}\\!")


@dp.message(Command("status"))
async def command_status(message: Message, bambu: BambuClient) -> None:
    """
    `/status` command
    """
    json = jsonpickle.encode(bambu.info, indent=4, unpicklable=False)
    await message.answer(f"ts: `{bambu.info.ts}`\n```json\n{json}\n```")


@dp.message(Command("photo"))
async def command_photo(message: Message, bambu: BambuClient) -> None:
    """
    `/photo` command
    """
    image = bambu.camera.image_buffer[-1] if bambu.camera.image_buffer else None

    if not image:
        await message.answer("No image")
        return

    await message.answer_photo(
        BufferedInputFile(image, "photo-moto"),
        caption=f"ts: `{bambu.info_ts}`",
        show_caption_above_media=True
    )


@dp.message()
async def echo_handler(message: Message) -> None:
    try:
        # Send a copy of the received message
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


@dp.startup()
async def on_startup(bambu: BambuClient) -> None:
    """
    Bot startup handler.
    Setup, initialize state, etc.
    """
    bambu.start()

    # todo: make buttons menu: status / ... / stop
    SetMyCommands(commands=[
        BotCommand(command="start", description="Start bot"),
        BotCommand(command="status", description="Check printer status"),
        BotCommand(command="photo", description="Get camera photo"),
        BotCommand(command="help", description="Help"),
    ])


@dp.shutdown()
async def on_shutdown(bambu: BambuClient) -> None:
    """
    Bot shutdown handler.
    Close connections, clean up.
    """
    await bambu.stop()


@dp.message.middleware()
async def auth_middleware(
    handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
    message: Message,
    state: Dict[str, Any]
) -> Any:
    """
    Chat id based auth.
    """
    if state["chat_id"] == message.chat.id:
        return await handler(message, state)
    else:
        return await message.answer(f"__*ACCESS DENIED*__\nchat id: `{message.chat.id}`")
