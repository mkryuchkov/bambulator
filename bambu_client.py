#!/usr/bin/env python
"""
Bambu printer client and monitor.
Based on https://github.com/mattcar15/bambu-connect by Matt Carroll.
"""

import json
import logging
import socket
import ssl
from typing import Any, Callable, Dict, Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class BambuClient:
    """Bambu printer client."""

    def __init__(self, hostname: str, access_code: str, serial: str):
        self.hostname = hostname
        self.serial = serial
        self.mqtt_port = 8883
        self.client = self.__setup_mqtt_client__(access_code)
        self.values = {}
        self.message_callback = None

    def __setup_mqtt_client__(self, access_code: str) -> mqtt.Client:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1, reconnect_on_failure=True)
        client.username_pw_set("bblp", access_code)
        client.tls_set(tls_version=ssl.PROTOCOL_TLS, cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
        client.on_connect = self._on_connect_cb_
        client.on_message = self._on_message_cb_  # todo: make ext cb
        client.on_connect_fail = self._on_connect_fail_cb_
        client.on_disconnect = self._on_disconnect_cb_  # todo: make ext cb
        return client

    def start(
        self,
        message_callback: Optional[Callable[[dict], None]] = None
    ) -> None:
        """Start printer client and connect."""
        self.message_callback = message_callback

        self.client.connect_async(self.hostname, self.mqtt_port, 60)
        self.client.loop_start()

    def stop(self) -> None:
        """Stop printer client."""
        self.client.disconnect()
        self.client.loop_stop()

    def _on_connect_cb_(self, client: mqtt.Client, *_) -> None:
        """Handles on_connect event."""
        # listen to stats responses
        client.subscribe(f"device/{self.serial}/report")
        logger.info(f"Connected to {self.hostname}")
        self._send_push_stats_command_()

    def _on_message_cb_(self, client: mqtt.Client, _, message: mqtt.MQTTMessage) -> None:
        """Handles incoming mqtt printer messages"""
        doc = json.loads(message.payload)
        try:
            if not doc:
                return

            self.values = dict(self.values, **doc["print"])

            if self.message_callback:
                self.message_callback(self.values)

        except KeyError as err:
            logger.error(f"Message receiving error: {err}")

    def _on_connect_fail_cb_(self, client: mqtt.Client, userdata: Any) -> None:
        logger.info("Connection failed")

    def _on_disconnect_cb_(self,
                           client: mqtt.Client,
                           userdata: Any,
                           code: mqtt.MQTTErrorCode) -> None:
        logger.info(f"Disconnected: {code.name}")

    def _send_push_stats_command_(self) -> None:
        """
        Get all the printer stats (incoming message event).
        For minor print updates the printer will send them automatically.
        """
        payload = '{"pushing": { "sequence_id": 1, "command": "pushall"}, "user_id":"1234567890"}'
        self.send_command(payload)

    def send_command(self, payload) -> None:
        """Send mqtt sommand to printer."""
        # todo: check if valid condition
        if (self.client.is_connected()):
            self.client.publish(f"device/{self.serial}/request", payload)
        else:
            logger.warning("Can't send command without active connection")

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
