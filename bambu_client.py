#!/usr/bin/env python
"""
Bambu printer client and monitor.
Based on https://github.com/mattcar15/bambu-connect by Matt Carroll.
"""

import asyncio
import datetime
import json
import logging
import math
import socket
import ssl
from types import SimpleNamespace

from aiomqtt import Client, MqttError, TLSParameters

from bambu_camera_client import BambuCameraClient

logger = logging.getLogger(__name__)


class BambuClient:
    """Bambu printer client."""

    def __init__(self, hostname: str, access_code: str, serial: str):
        self.hostname = hostname
        self.access_code = access_code
        self.report_topic = f"device/{serial}/report"
        self.request_topic = f"device/{serial}/request"
        self.info = None
        self.info_ts = None
        self.running = False
        self.camera = BambuCameraClient(hostname, access_code)

    def start(self):
        """Start printer client and connect."""
        self.running = True
        self.main = asyncio.create_task(self.listen_loop())
        self.camera.start()

    async def stop(self):
        """Stop printer client."""
        self.main.cancel()
        await self.main
        self.running = False
        await self.camera.stop()

    async def listen_loop(self):
        while (self.running):
            try:
                async with self._create_mqtt_client_() as client:

                    await client.subscribe(self.report_topic, timeout=math.inf)
                    logger.info(f"Connected to {client._hostname}")

                    async for message in client.messages:
                        doc = json.loads(
                            message.payload, object_hook=lambda d: SimpleNamespace(**d))

                        if doc.print:
                            self.info = doc.print
                            self.info.ts = datetime.datetime.now(datetime.UTC)

                            # todo: async callback -> (current, diff)

                        await client.publish(self.request_topic, '{"pushing": { "sequence_id": 1, "command": "pushall"}, "user_id":"1234567890"}')

            except MqttError as err:
                logger.warning(f"MqttError: {err}")

            except Exception as ex:
                logger.error(f"Unhandled exception {
                    type(ex)} Args: {ex}")

            # todo: check if online // progressive reconnect delay // stop/start video client too
            await asyncio.sleep(1)

    def is_online(self) -> bool:
        """Check if printer host is online."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)

            result = sock.connect_ex((self.hostname, self.mqtt_port))
            sock.close()

            return result == 0  # 0 means the connection was successful
        except socket.error:
            return False

    def _create_mqtt_client_(self):
        return Client(
            hostname=self.hostname,
            port=8883,
            username="bblp",
            password=self.access_code,
            tls_params=TLSParameters(
                tls_version=ssl.PROTOCOL_TLS, cert_reqs=ssl.CERT_NONE),
            tls_insecure=True,
            keepalive=5
        )
