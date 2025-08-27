# queue_print.py
import os, json, time, threading, traceback
from typing import Optional, Dict, Any, List
from pathlib import Path

from logic import mqtt_publish_image_base64  # nutzt dein bestehendes Publish

QUEUE_DIR = Path(os.getenv("PRINT_QUEUE_DIR", "/data/print-queue"))  # auf Render bleibt /data ueber Deploys bestehen
QUEUE_DIR.mkdir(parents=True, exist_ok=True)

SLEEP_SECONDS = int(os.getenv("PRINT_QUEUE_POLL", "20"))  # alle 20s versuchen
_running = False
_thread: Optional[threading.Thread] = None

def _job_path(ts: float) -> Path:
    # ts als sortierbarer name
    return QUEUE_DIR / f"{int(ts*1000)}.json"

def enqueue_base64_png(b64png: str, cut_paper: int = 1, meta: Optional[Dict[str, Any]] = None) -> Path:
    meta = meta or {}
    payload = {"b64": b64png, "cut": int(cut_paper), "meta": meta, "ts": time.time()}
    p = _job_path(payload["ts"])
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return p

def dequeue_one() -> Optional[Path]:
    files = sorted(QUEUE_DIR.glob("*.json"))
    return files[0] if files else None

def _try_publish(path: Path) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            job = json.load(f)
        mqtt_publish_image_base64(job["b64"], cut_paper=int(job.get("cut", 1)))
        # wenn kein Fehler geworfen wird, werten wir als erfolgreich
        path.unlink(missing_ok=True)
        return True
    except Exception:
        # Debug optional ins Logfile
        traceback.print_exc()
        return False

def flush_once(max_n: int = 10) -> int:
    n = 0
    for _ in range(max_n):
        p = dequeue_one()
        if not p:
            break
        ok = _try_publish(p)
        if not ok:
            # Abbrechen und spaeter erneut versuchen
            break
        n += 1
    return n

def _loop():
    global _running
    while _running:
        try:
            flushed = flush_once(20)
        except Exception:
            flushed = 0
        time.sleep(SLEEP_SECONDS if flushed == 0 else 1)

def start_background_flusher():
    global _running, _thread
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_loop, name="print-queue-flusher", daemon=True)
    _thread.start()

def stop_background_flusher():
    global _running
    _running = False
