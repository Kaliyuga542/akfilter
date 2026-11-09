import logging
import logging.config
import os
import sys
import asyncio
from datetime import date, datetime
import pytz
import aiohttp

# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.CRITICAL - 1)

import tgcrypto
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from database.ia_filterdb import Media
from database.users_chats_db import db
from info import SESSION, API_ID, API_HASH, BOT_TOKEN, LOG_STR, LOG_CHANNEL, KEEP_ALIVE_URL, DEFAULT_AUTH_CHANNELS
from utils import temp
from typing import Union, Optional, AsyncGenerator
from pyrogram import types
from Script import script
from os import environ
from aiohttp import web as webserver

# Peer ID invalid fix
from pyrogram import utils as pyroutils
pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999

from plugins.webcode import bot_run

# Render & Koyeb auto port binding
PORT_CODE = int(environ.get("PORT", "8080"))

async def preload_auth_channels():
    if not await db.get_auth_channels():
        await db.set_auth_channels(DEFAULT_AUTH_CHANNELS)
        logging.info("Set default AUTH_CHANNELs in DB.")

async def keep_alive():
    """Send a request every 5 minutes to prevent Render/Koyeb sleeping"""
    await asyncio.sleep(30) # Bot server poorthi start aago varege wait madalu
    async with aiohttp.ClientSession() as session:
        while True:
            url = environ.get("KEEP_ALIVE_URL", KEEP_ALIVE_URL)
            if url and url.startswith("http"):
                try:
                    async with session.get(url, timeout=10) as resp:
                        logging.info(f"Keep-alive ping sent to {url} | Status: {resp.status}")
                except Exception as e:
                    logging.error(f"Keep-alive request failed: {e}")
            else:
                logging.warning("KEEP_ALIVE_URL set agilla athava invalid ide.")
            # 5 minutes (300 seconds) ge ondsala ping maduthe
            await asyncio.sleep(300)

class Bot(Client):

    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )

    async def kulasthree(self):
        while True:
            await asyncio.sleep(24 * 60 * 60)
            logging.info("🔄 Bot is restarting")
            await self.send_message(chat_id=LOG_CHANNEL, text="🔄 Bot is restarting ...")
            os.execl(sys.executable, sys.executable, *sys.argv)

    async def start(self, **kwargs):
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        await super().start()
        await Media.ensure_indexes()
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        self.username = '@' + me.username

        await preload_auth_channels()

        logging.info(f"{me.first_name} running on Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
        logging.info(LOG_STR)
        await self.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT)

        tz = pytz.timezone('Asia/Kolkata')
        today = date.today()
        now = datetime.now(tz)
        time = now.strftime("%H:%M:%S %p")
        await self.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_GC_TXT.format(today, time))

        # Background 24/7 tasks
        asyncio.create_task(self.kulasthree())
        asyncio.create_task(keep_alive())

        # Web server binding for Render / Koyeb
        app = await bot_run()
        client = webserver.AppRunner(app)
        await client.setup()
        site = webserver.TCPSite(client, "0.0.0.0", PORT_CODE)
        await site.start()
        logging.info(f"Web server successfully bound to port {PORT_CODE}")

    async def stop(self, *args):
        await super().stop()
        logging.info("Bot stopped. Bye.")

    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current + new_diff + 1)))
            for message in messages:
                yield message
                current += 1

app = Bot()
app.run()
