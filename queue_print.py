# queue_print.py — persistente Druck-Queue mit Auto-Flush & optionalem WLAN-Direktdruck
import os, json, time, threading, traceback
from pathlib import Path
from typing import Optional, Dict, Any

from logic import mqtt_publish_image_base64  # MQTT fallback
from logic import print_base64_png_direct     # direkter WLAN-Druck (wenn verfügbar)

# ----------------- Konfiguration -----------------

# Pfad zur Drucker-Queue (persistente JSON-Dateien)
PRINT_QUEUE_DIR = os.getenv("PRINT_QUEUE_DIR", "/tmp/print-queue")
QUEUE_DIR = Path(PRINT_QUEUE_DIR)

# Druckversuch alle X Sekunden
SLEEP_SECONDS = int(os.getenv("PRINT_QUEUE_POLL", "20"))

# Falls PRINTER_IP gesetzt ist → direkter Druck, sonst MQTT
PRINTER_IP = os.getenv("PRINTER_IP")

_running = False
_thread: Optional[threading.Thread] = None


# ----------------- Helper -----------------

def _ensure_dir():
    """Sorgt dafür, dass das Queue-Verzeichnis existiert."""
    try:
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _job_path(ts: float) -> Path:
    """Erzeugt eindeutigen Dateinamen."""
    return QUEUE_DIR / f"{int(ts * 1000)}.json"


def enqueue_base64_png(b64png: str, cut_paper: int = 1, meta: Optional[Dict[str, Any]] = None) -> Optional[Path]:
    """Speichert ein Druck-Job als JSON-Datei persistiert."""
    _ensure_dir()
    meta = meta or {}
    payload = {"b64": b64png, "cut": int(cut_paper), "meta": meta, "ts": time.time()}
    try:
        p = _job_path(payload["ts"])
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        print(f"[queue] 💾 Ticket gespeichert: {p.name}")
        return p
    except Exception:
        traceback.print_exc()
        return None


def _dequeue_one() -> Optional[Path]:
    """Lädt das älteste Job-File aus der Queue."""
    try:
        files = sorted(QUEUE_DIR.glob("*.json"))
        return files[0] if files else None
    except Exception:
        return None


# ----------------- Drucklogik -----------------

def _try_publish(path: Path) -> bool:
    """Versucht, ein Ticket zu drucken (direkt oder über MQTT)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            job = json.load(f)
    except json.JSONDecodeError:
        print(f"[queue] 🗑️ Korrupte JSON-Datei erkannt und gelöscht: {path.name}")
        path.unlink(missing_ok=True)
        return False
    except Exception as e:
        print(f"[queue] ⚠️ Fehler beim Lesen von {path.name}: {e}")
        return False

    try:
        b64 = job["b64"]
        cut = int(job.get("cut", 1))

        # Direkter Netzwerkdruck bevorzugt, wenn PRINTER_IP vorhanden
        if PRINTER_IP:
            ok = print_base64_png_direct(b64, cut_paper=cut)
        else:
            ok = mqtt_publish_image_base64(b64, cut_paper=cut)

        if ok is not False:  # True oder None = Erfolg
            print(f"[queue] 🖨️ Ticket gedruckt: {path.name}")
            path.unlink(missing_ok=True)
            return True
        else:
            print(f"[queue] ⚠️ Druck fehlgeschlagen, bleibt in Queue: {path.name}")
            return False
    except Exception:
        traceback.print_exc()
        return False


# ----------------- Loop / Background Thread -----------------

def flush_once(max_n: int = 10) -> int:
    """Versucht, bis zu max_n Tickets aus der Queue zu drucken."""
    _ensure_dir()
    n = 0
    for _ in range(max_n):
        p = _dequeue_one()
        if not p:
            break
        if not _try_publish(p):
            break  # wenn ein Job fehlschlägt, abbrechen (Drucker evtl. offline)
        n += 1
    return n


def _loop():
    """Hintergrundschleife für den Druck-Queue-Flush."""
    global _running
    while _running:
        flushed = 0
        try:
            flushed = flush_once(20)
        except Exception:
            traceback.print_exc()
        # Wenn nichts gedruckt wurde → Pause
        time.sleep(SLEEP_SECONDS if flushed == 0 else 1)


# ----------------- Steuerfunktionen -----------------

def start_background_flusher():
    """Startet den Hintergrund-Thread für den Queue-Flush."""
    global _running, _thread
    if _running:
        return
    _ensure_dir()
    _running = True
    _thread = threading.Thread(target=_loop, name="print-queue-flusher", daemon=True)
    _thread.start()
    print("[queue] ♻️ Hintergrund-Queue gestartet.")


def stop_background_flusher():
    """Stoppt die Queue-Verarbeitung."""
    global _running
    _running = False
    print("[queue] 🛑 Queue-Loop gestoppt.")
