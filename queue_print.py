# queue_print.py — MongoDB-based Queue mit "Last 20"-Limit & Offline-Schutz
import os
import time
import threading
import traceback
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# Wir nutzen die Mongo-Verbindung und MQTT-Logik aus logic.py
from logic import (
    mqtt_publish_image_base64,
    _get_settings_collection, # Wir nutzen die bestehende Connection-Logik
    printer_status,           # Um zu prüfen, ob der Drucker online ist
    log
)

# ----------------- Konfiguration -----------------

# Wie oft prüfen, ob neue Tickets da sind?
SLEEP_SECONDS = int(os.getenv("PRINT_QUEUE_POLL", "10"))

# Maximale Anzahl Tickets, die gedruckt werden (Rest wird übersprungen)
MAX_QUEUE_SIZE = 20

_running = False
_thread: Optional[threading.Thread] = None

# ----------------- MongoDB Helpers -----------------

def _get_db():
    """Holt die Datenbank-Referenz (nutzt den Client aus logic.py)."""
    # _get_settings_collection gibt uns 'printer.settings'. 
    # Wir hangeln uns zur DB hoch.
    coll = _get_settings_collection()
    if coll is not None:
        return coll.database
    return None

def _get_queue_coll():
    db = _get_db()
    return db["queue"] if db is not None else None

def _get_archive_coll():
    db = _get_db()
    return db["archive"] if db is not None else None

# ----------------- Public API -----------------

def enqueue_base64_png(b64png: str, cut_paper: int = 1, meta: Optional[Dict[str, Any]] = None) -> bool:
    """Speichert ein neues Ticket in der MongoDB-Queue."""
    coll = _get_queue_coll()
    if coll is None:
        log("❌ [Queue] Keine Verbindung zu MongoDB! Ticket verloren.")
        return False

    meta = meta or {}
    payload = {
        "b64": b64png,
        "cut": int(cut_paper),
        "meta": meta,
        "ts": time.time(),
        "status": "pending"
    }
    
    try:
        coll.insert_one(payload)
        log(f"[Queue] 💾 Ticket in MongoDB gespeichert (Quelle: {meta.get('source', 'unknown')})")
        return True
    except Exception as e:
        log(f"❌ [Queue] Fehler beim Speichern: {e}")
        return False

# ----------------- Migration (File -> Mongo) -----------------

def migrate_files_to_mongo():
    """
    Sucht nach alten .json-Dateien im PRINT_QUEUE_DIR,
    schiebt sie in die Mongo-Queue und löscht die Dateien.
    Wird beim Start einmal ausgeführt.
    """
    queue_dir_str = os.getenv("PRINT_QUEUE_DIR", "/tmp/print-queue")
    queue_dir = Path(queue_dir_str)
    
    if not queue_dir.exists():
        return

    log("[Queue] 📂 Prüfe auf alte Queue-Dateien zur Migration...")
    
    files = sorted(queue_dir.glob("*.json"))
    if not files:
        return

    coll = _get_queue_coll()
    if coll is None:  # <--- KORRIGIERT (war 'if not coll:')
        log("⚠️ [Queue] Kann nicht migrieren – Keine DB-Verbindung.")
        return

    count = 0
    for p in files:
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Struktur anpassen falls nötig
            if "b64" in data:
                doc = {
                    "b64": data["b64"],
                    "cut": int(data.get("cut", 1)),
                    "meta": data.get("meta", {}),
                    "ts": data.get("ts", time.time()),
                    "status": "migrated_from_file"
                }
                coll.insert_one(doc)
                p.unlink() # Datei löschen
                count += 1
        except Exception as e:
            log(f"⚠️ Fehler bei Migration von {p.name}: {e}")
    
    if count > 0:
        log(f"[Queue] ✅ {count} alte Tickets erfolgreich in MongoDB migriert.")

# ----------------- Flush Logic -----------------

def _clean_overflow_queue():
    """
    Stellt sicher, dass nicht mehr als MAX_QUEUE_SIZE Tickets warten.
    Ältere Tickets werden ins Archiv verschoben (übersprungen).
    """
    q_coll = _get_queue_coll()
    a_coll = _get_archive_coll()
    # KORRIGIERT: Expliziter Check auf None statt 'not object'
    if q_coll is None or a_coll is None:
        return

    try:
        count = q_coll.count_documents({})
        if count > MAX_QUEUE_SIZE:
            excess = count - MAX_QUEUE_SIZE
            log(f"[Queue] 🧹 Queue zu voll ({count}). Lösche {excess} alte Tickets...")
            
            # Die ältesten 'excess' Tickets finden
            # Sortierung: 1 = aufsteigend (älteste zuerst)
            cursor = q_coll.find().sort("ts", 1).limit(excess)
            
            to_move = []
            ids_to_remove = []
            for doc in cursor:
                doc["archived_at"] = time.time()
                doc["reason"] = "skipped_overflow" # Markierung warum nicht gedruckt
                to_move.append(doc)
                ids_to_remove.append(doc["_id"])
            
            if to_move:
                a_coll.insert_many(to_move)
                q_coll.delete_many({"_id": {"$in": ids_to_remove}})
                log(f"[Queue] 🗑️ {len(to_move)} alte Tickets archiviert (nicht gedruckt).")
    except Exception as e:
        log(f"❌ [Queue] Fehler beim Bereinigen: {e}")

def flush_once():
    """
    Verarbeitet die Queue. 
    Druckt NUR, wenn printer_status sagt 'online'.
    """
    # 1. Check: Ist Drucker online?
    status = printer_status()
    if not status.get("online", False):
        return 0

    q_coll = _get_queue_coll()
    a_coll = _get_archive_coll()
    
    # KORRIGIERT: Expliziter Check auf None
    if q_coll is None:
        return 0

    # 2. Aufräumen (Chaos-Schutz)
    _clean_overflow_queue()

    # 3. Die (jetzt maximal 20) Tickets holen
    # Wir sortieren nach TS aufsteigend (ältestes zuerst), damit die Reihenfolge stimmt
    jobs = list(q_coll.find().sort("ts", 1).limit(MAX_QUEUE_SIZE))
    
    if not jobs:
        return 0

    printed_count = 0
    for job in jobs:
        try:
            b64 = job["b64"]
            cut = job.get("cut", 1)
            
            # Senden an MQTT
            mqtt_publish_image_base64(b64, cut_paper=cut)
            
            # Verschieben ins Archiv
            job["archived_at"] = time.time()
            job["reason"] = "sent_to_mqtt"
            
            # KORRIGIERT: Expliziter Check auf None
            if a_coll is not None:
                a_coll.insert_one(job)
            
            q_coll.delete_one({"_id": job["_id"]})
            
            log(f"[Queue] 📤 Ticket an MQTT gesendet (ID: {str(job['_id'])[-6:]})")
            printed_count += 1
            
            # Kurze Pause zwischen Tickets
            time.sleep(2) 
            
        except Exception as e:
            log(f"❌ [Queue] Fehler beim Verarbeiten von Ticket {job.get('_id')}: {e}")
            break # Loop abbrechen, später nochmal versuchen

    return printed_count

# ----------------- Thread Loop -----------------

def _loop():
    global _running
    while _running:
        try:
            flush_once()
        except Exception as e:
            traceback.print_exc()
        
        time.sleep(SLEEP_SECONDS)

def start_background_flusher():
    global _running, _thread
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_loop, name="mongo-queue-flusher", daemon=True)
    _thread.start()
    log("[Queue] ♻️ MongoDB-Queue-Thread gestartet.")

def stop_background_flusher():
    global _running
    _running = False
    log("[Queue] 🛑 Queue-Loop gestoppt.")
