import os
import socket
import threading
import time
from typing import Callable


def _default_log(*args):
    print("[status]", *args, flush=True)


class PrinterStatusMonitor:
    """
    Tracks printer presence using passive MQTT heartbeats and active probes.
    A lightweight wrapper so core logic can simply delegate status queries.
    """

    def __init__(self, log_fn: Callable[..., None] | None = None):
        self._log = log_fn or _default_log
        self._lock = threading.Lock()
        self._last_seen = 0.0
        self._last_status: dict[str, object] | None = None
        self._last_probe = 0.0
        self._client = None

        # Topics & behavior from environment
        self.heartbeat_topic = os.getenv("PRINTER_HEARTBEAT_TOPIC", "Hearbeat")
        self.print_success_topics = {
            os.getenv("PRINT_SUCCESS_TOPIC", "PrintSuccess"),
            os.getenv("PRINT_SUCCESS_ALT_TOPIC", "PrintSucces"),
        }
        self.printer_topic = os.getenv("PRINTER_TOPIC", "Prn20B1B50C2199")
        self.printer_ip = os.getenv("PRINTER_IP")
        self.printer_port = int(os.getenv("PRINTER_PORT", "9100"))

        self.heartbeat_online_window = float(os.getenv("PRINTER_HEARTBEAT_WINDOW", "60"))
        self.status_cache_secs = int(os.getenv("PRINTER_STATUS_CACHE", "25"))
        self.tcp_timeout = float(os.getenv("PRINTER_STATUS_TCP_TIMEOUT", "2.5"))
        self.active_probe_interval = float(os.getenv("PRINTER_PROBE_INTERVAL", "10"))

    # ---- Wiring helpers -------------------------------------------------- #
    def set_logger(self, log_fn: Callable[..., None]) -> None:
        self._log = log_fn or _default_log

    def attach_client(self, client) -> None:
        """Provide a connected paho-mqtt client."""
        self._client = client

    def subscription_topics(self, qos: int) -> list[tuple[str, int]]:
        topics = {(self.heartbeat_topic, min(1, qos or 0))}
        for t in self.print_success_topics:
            topics.add((t, 1))
        return list(topics)

    # ---- State tracking -------------------------------------------------- #
    def mark_seen(self, ts: float | None = None) -> None:
        with self._lock:
            self._last_seen = ts or time.time()

    def last_seen(self) -> float:
        with self._lock:
            return self._last_seen

    def handle_message(self, topic: str | bytes, _payload: bytes | None = None) -> bool:
        """Returns True if the topic was consumed for presence tracking."""
        t = topic.decode("utf-8", errors="ignore") if isinstance(topic, (bytes, bytearray)) else str(topic)
        if t == self.heartbeat_topic or t in self.print_success_topics:
            self.mark_seen()
            return True
        return False

    # ---- Probing --------------------------------------------------------- #
    def _probe_printer_tcp(self) -> tuple[bool, str]:
        try:
            with socket.create_connection((self.printer_ip, self.printer_port), timeout=self.tcp_timeout):
                return True, f"TCP {self.printer_ip}:{self.printer_port} reachable"
        except Exception as e:
            return False, f"TCP probe failed: {e}" if str(e) else "TCP probe failed"

    def _send_printer_probe(self, now: float) -> tuple[bool, str]:
        c = self._client
        if c is None:
            return False, "MQTT client not initialized"
        if hasattr(c, "is_connected") and not c.is_connected():
            return False, "MQTT disconnected"
        with self._lock:
            if now - self._last_probe < self.active_probe_interval:
                return False, "Probe throttled"
            self._last_probe = now
        try:
            info = c.publish(self.printer_topic, b"\x01\x00", qos=1, retain=False)
            rc = getattr(info, "rc", 0)
            if rc != 0:
                return False, f"MQTT publish rc={rc}"
            return True, "Active MQTT probe sent"
        except Exception as e:
            return False, f"MQTT probe failed: {e}"

    # ---- Public status --------------------------------------------------- #
    def status(self, force: bool = False) -> dict[str, object]:
        now = time.time()
        last_seen = self.last_seen()
        delta = now - last_seen if last_seen else float("inf")

        detail_parts: list[str] = []
        if last_seen:
            detail_parts.append(f"Last heartbeat {delta:.1f}s ago.")
        else:
            detail_parts.append("No heartbeat received yet.")

        # Passive heartbeat dominates
        if delta < self.heartbeat_online_window:
            self._last_status = {
                "online": True,
                "checked_at": now,
                "method": "mqtt_heartbeat",
                "detail": "Heartbeat fresh.",
                "last_seen": last_seen,
            }
            return self._last_status

        # Active MQTT probe
        probe_ok, probe_detail = self._send_printer_probe(now)
        detail_parts.append(probe_detail)
        method = "mqtt_probe"
        online = False

        # TCP as final check if configured
        if self.printer_ip:
            if (
                not force
                and self._last_status
                and self._last_status.get("method") == "tcp"
                and now - float(self._last_status.get("checked_at", 0)) < self.status_cache_secs
            ):
                return self._last_status
            tcp_online, tcp_detail = self._probe_printer_tcp()
            online = tcp_online
            method = "tcp"
            detail_parts.append(tcp_detail)

        self._last_status = {
            "online": bool(online),
            "checked_at": now,
            "method": method,
            "detail": " ".join(detail_parts),
            "last_seen": last_seen,
        }
        return self._last_status


monitor = PrinterStatusMonitor()


def set_logger(log_fn: Callable[..., None]) -> None:
    monitor.set_logger(log_fn)


def attach_client(client) -> None:
    monitor.attach_client(client)


def handle_presence_message(topic: str | bytes, payload: bytes | None = None) -> bool:
    return monitor.handle_message(topic, payload)


def subscription_topics(qos: int) -> list[tuple[str, int]]:
    return monitor.subscription_topics(qos)


def printer_status(force: bool = False) -> dict[str, object]:
    return monitor.status(force)
