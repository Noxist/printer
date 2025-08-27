# queue_print.py
import os, json, time, threading, traceback
from typing import Optional, Dict, Any
from pathlib import Path

from logic import mqtt_publish_image_base64  # bestehend

# Schreibbarer Default:
# - Render: /tmp ist immer beschreibbar (ephemeral)
# - Kann per ENV ueberschrieben werden (z. B. wenn du einen Persistent Disk Mount nutzt)
PRINT_QUEUE_DIR = os.getenv("PRINT_QUEUE_DIR", "/tmp/print-queue")
QUEUE_DIR = Path(PRINT_QUEUE_DIR)

SLEEP_SECONDS = int(os.getenv("PRINT_QUEUE_POLL", "20"))  # alle 20s versuchen
_running = False
_thread: Optional[threading.Thread] = None

def _ensure_dir():
    try:
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Falls das Verzeichnis nicht angelegt werden kann, nicht crashen – spaeter erneut versuchen
        pass

def _job_path(ts: float) -> Path:
    return QUEUE_DIR / f"{int(ts*1000)}.json"

def enqueue_base64_png(b64png: str, cut_paper: int = 1, meta: Optional[Dict[str, Any]] = None) -> Optional[Path]:
    _ensure_dir()
    meta = meta or {}
    payload = {"b64": b64png, "cut": int(cut_paper), "meta": meta, "ts": time.time()}
    try:
        p = _job_path(payload["ts"])
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        return p
    except Exception:
        traceback.print_exc()
        return None

def _dequeue_one() -> Optional[Path]:
    try:
        files = sorted(QUEUE_DIR.glob("*.json"))
        return files[0] if files else None
    except Exception:
        return None

def _try_publish(path: Path) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            job = json.load(f)
        mqtt_publish_image_base64(job["b64"], cut_paper=int(job.get("cut", 1)))
        path.unlink(missing_ok=True)
        return True
    except Exception:
        traceback.print_exc()
        return False

def flush_once(max_n: int = 10) -> int:
    _ensure_dir()
    n = 0
    for _ in range(max_n):
        p = _dequeue_one()
        if not p:
            break
        if not _try_publish(p):
            break
        n += 1
    return n

def _loop():
    global _running
    while _running:
        flushed = 0
        try:
            flushed = flush_once(20)
        except Exception:
            traceback.print_exc()
        time.sleep(SLEEP_SECONDS if flushed == 0 else 1)

def start_background_flusher():
    """ Beim App-Startup aufrufen """
    global _running, _thread
    if _running:
        return
    _ensure_dir()
    _running = True
    _thread = threading.Thread(target=_loop, name="print-queue-flusher", daemon=True)
    _thread.start()

def stop_background_flusher():
    global _running
    _running = False
