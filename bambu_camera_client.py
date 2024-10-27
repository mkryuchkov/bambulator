#!/usr/bin/env python
"""
Bambu camera client.
Based on https://github.com/mattcar15/bambu-connect by Matt Carroll
and https://github.com/synman/bambu-go2rtc by Shell M. Shrader
"""

import collections
import logging
import struct
import socket
import ssl
import time
import threading
from typing import Callable, Optional

JPEG_START = bytearray([0xff, 0xd8, 0xff, 0xe0])
JPEG_END = bytearray([0xff, 0xd9])

logger = logging.getLogger(__name__)


class BambuCameraClient:
    def __init__(self, hostname: str, access_code: str):
        self.hostname = hostname
        self.port = 6000
        self.auth_packet = self.__create_auth_packet__(access_code=access_code)
        self.streaming = False
        self.stream_thread = None
        self.image_callback = None
        self.image_buffer = collections.deque(maxlen=10)

    def __create_auth_packet__(self, username: str = "bblp", access_code: str = None):
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

    def start(self, image_callback: Optional[Callable[[bytearray], None]] = None):
        if self.streaming:
            logger.warning("Stream is already running")
            return

        self.image_callback = image_callback
        self.streaming = True
        self.stream_thread = threading.Thread(target=self.capture_loop)
        self.stream_thread.start()

    def stop(self):
        if not self.streaming:
            logger.warning("Stream is not running")
            return

        self.streaming = False
        self.stream_thread.join()

    def capture_loop(self):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        while self.streaming:
            try:
                with socket.create_connection((self.hostname, self.port)) as sock:
                    try:
                        sslSock = ctx.wrap_socket(
                            sock, server_hostname=self.hostname)
                        sslSock.write(self.auth_packet)
                        status = sslSock.getsockopt(
                            socket.SOL_SOCKET, socket.SO_ERROR)

                        if status != 0:
                            logger.debug(f"Socket error: {status}")
                            pass
                    except socket.error as e:
                        logger.debug(f"Socket error: {e}")
                        pass

                    sslSock.setblocking(False)

                    self.read_image_loop(sslSock)

            except Exception as e:
                logger.error(f"Unhandled exception. Type: {type(e)} Args: {e}")
                time.sleep(1)

    def read_image_loop(self, sock: socket):
        current_image = None
        payload_size = 0

        while self.streaming:
            try:
                chunk = sock.recv(4096)
            except ssl.SSLWantReadError:
                logger.debug("SSLWantReadError")
                # time.sleep(1)
                continue
            except Exception as e:
                logger.debug(f"Reading chunk error: {
                    type(e)} Args: {e}")
                # time.sleep(1)
                continue

            if current_image is not None and len(chunk) > 0:
                current_image += chunk
                if len(current_image) > payload_size:
                    logger.error(f"Unexpected image payload received: {
                        len(current_image)} > {payload_size}")
                    current_image = None
                elif len(current_image) == payload_size:
                    if current_image[:4] == JPEG_START and current_image[-2:] == JPEG_END:
                        self.image_buffer.append(current_image)
                        if (self.image_callback):
                            self.image_callback(current_image)
                    else:
                        logger.debug("No JPEG image detected")

                    current_image = None

            elif len(chunk) == 16:
                current_image = bytearray()
                payload_size = int.from_bytes(
                    chunk[0:3], byteorder='little')

            elif len(chunk) == 0:
                logger.error(
                    "Connection rejected. Check access code and IP address.")
                time.sleep(5)
                break

            else:
                logger.error(
                    f"Unexpected data received: {len(chunk)}")
                time.sleep(1)
                break
