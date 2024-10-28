#!/usr/bin/env python
"""
Bambu camera client.
Based on https://github.com/mattcar15/bambu-connect by Matt Carroll
and https://github.com/synman/bambu-go2rtc by Shell M. Shrader
"""

import asyncio
import collections
import logging
import struct
import ssl

JPEG_START = bytearray([0xff, 0xd8, 0xff, 0xe0])
JPEG_END = bytearray([0xff, 0xd9])

logger = logging.getLogger(__name__)


class BambuCameraClient:
    """Bambu printer camera client"""

    def __init__(self, hostname: str, access_code: str):
        self.hostname = hostname
        self.port = 6000
        self.auth_packet = self.__create_auth_packet__(access_code=access_code)
        self.streaming = False
        self.image_buffer = collections.deque(maxlen=10)
        self.task = None
        self.ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def start(self):
        """Connect to printer and start capture loop"""
        if self.streaming:
            logger.warning("Stream is already running")
            return

        self.streaming = True
        self.main = asyncio.create_task(self.capture_loop())

    async def stop(self):
        """Stop capture loop"""
        if not self.streaming:
            logger.warning("Stream is not running")
            return

        self.streaming = False
        self.main.cancel()
        await self.main

    async def capture_loop(self):
        """Image capture loop"""
        while self.streaming:
            try:
                async with asyncio.timeout(2):
                    reader, writer = await asyncio.open_connection(
                        self.hostname, self.port, limit=256000)
                    await writer.start_tls(self.ssl_ctx, server_hostname=self.hostname)
                    writer.write(self.auth_packet)

                logger.info(f"Connected to {self.hostname}")

                while True:
                    async with asyncio.timeout(5):
                        buffer = await reader.readuntil(JPEG_END)
                    start = buffer.find(JPEG_START)
                    logger.debug(f'Readed {len(buffer)} bytes until JPEG_END')
                    if start > 0:
                        self.image_buffer.append(buffer[start:])
                    else:
                        logger.warning(f"Shit in buffer; len={len(buffer)}")

            # todo: TimeoutError from asyncio.timeout
            except Exception as e:
                logger.error(f"Unhandled exception. Type: {type(e)} Args: {e}")

                # todo: check if online // progressive reconnect delay
                await asyncio.sleep(1)

    def __create_auth_packet__(self, username: str = "bblp", access_code: str = None):
        """Create bambu auth packet"""
        auth_data = bytearray()
        auth_data += struct.pack("<I", 0x40)  # '@'\0\0\0
        auth_data += struct.pack("<I", 0x3000)  # \0'0'\0\0
        auth_data += struct.pack("<I", 0)  # \0\0\0\0
        auth_data += struct.pack("<I", 0)  # \0\0\0\0
        for i in range(0, len(username)):
            auth_data += struct.pack("<c", username[i].encode('ascii'))
        for i in range(0, 32 - len(username)):
            auth_data += struct.pack("<x")
        for i in range(0, len(access_code)):
            auth_data += struct.pack("<c", access_code[i].encode('ascii'))
        for i in range(0, 32 - len(access_code)):
            auth_data += struct.pack("<x")
        return auth_data
