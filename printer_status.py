# printer_status.py
import socket
import time
import threading
import os
from logic import log

class PrinterStatus:
    def __init__(self):
        self.ip = os.getenv("PRINTER_IP")
        # Standard port for raw printing is 9100
        self.port = 9100 
        self.is_online = False
        self._running = False
        self._thread = None

    def start(self):
        """Starts the background checker thread."""
        if not self.ip:
            log("⚠️ PRINTER_IP not set. Status checker disabled (Status: Unknown).")
            # If no IP is set, we can't check, so we leave it as False or maybe True if you use MQTT exclusively.
            # Assuming False (Offline) for safety if direct IP is missing.
            return

        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="PrinterStatus")
        self._thread.start()
        log(f"✅ Printer status checker started for {self.ip}:{self.port}")

    def stop(self):
        """Stops the background checker."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        log("🛑 Printer status checker stopped.")

    def _loop(self):
        while self._running:
            self.is_online = self._check()
            # Sleep 10 seconds between checks to save resources
            time.sleep(10)

    def _check(self) -> bool:
        """Tries to open a socket to the printer. Returns True if successful."""
        try:
            # Low timeout (2s) to prevent blocking the thread for long
            with socket.create_connection((self.ip, self.port), timeout=2):
                return True
        except (OSError, socket.timeout):
            return False
        except Exception as e:
            log(f"⚠️ Status check error: {e}")
            return False

# Global instance to be imported by main.py
status_checker = PrinterStatus()
