# guest_tokens.py
# Vollständige Endversion – Datei- und MongoDB-Backend integriert
# Entwickelt für Leandro Aeschbacher – 2025

from __future__ import annotations
import os
import json
import time
import secrets
from typing import Dict, Any, List, Tuple, Optional

# ============================================================
# ==============  LOKALES DATEI-BACKEND  =====================
# ============================================================

class GuestDB:
    """
    Einfache Token-Datenbank mit Tageskontingent, lokal als JSON gespeichert.

    JSON-Struktur:
    {
      "tokens": {
        "tokenstring": {
          "name": "Yaralie",
          "created": 1710000000,
          "active": true,
          "quota_per_day": 5,
          "used": { "2025-08-25": 3, ... }
        },
        ...
      }
    }
    """

    def __init__(self, path: str = "guest_tokens.json"):
        self.path = path
        self.data: Dict[str, Any] = {"tokens": {}}
        self._load()

    # ---------------------- Persistence ----------------------

    def _load(self):
        """Lädt bestehende JSON-Datei, falls vorhanden."""
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
                if "tokens" not in self.data:
                    self.data["tokens"] = {}
        except Exception:
            self.data = {"tokens": {}}

    def _save(self):
        """Speichert Änderungen atomar."""
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # ---------------------- Utilities -----------------------

    @staticmethod
    def _today() -> str:
        """Heutiges Datum als YYYY-MM-DD."""
        return time.strftime("%Y-%m-%d")

    @staticmethod
    def _now_ts() -> int:
        """Aktueller UNIX-Zeitstempel."""
        return int(time.time())

    # ---------------------- Public API ----------------------

    def create(self, name: str, quota_per_day: int = 5) -> str:
        """Erstellt einen neuen Gast-Token."""
        token = secrets.token_urlsafe(24)
        self.data["tokens"][token] = {
            "name": name.strip() or "Gast",
            "created": self._now_ts(),
            "active": True,
            "quota_per_day": int(quota_per_day),
            "used": {}
        }
        self._save()
        return token

    def revoke(self, token: str) -> bool:
        """Deaktiviert einen bestehenden Token."""
        tok = self.data["tokens"].get(token)
        if not tok:
            return False
        tok["active"] = False
        self._save()
        return True

    def list(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Gibt alle Tokens zurück (token, info)."""
        return sorted(
            self.data["tokens"].items(),
            key=lambda kv: kv[1].get("created", 0),
            reverse=True
        )

    def remaining_today(self, token: str) -> int:
        """Wie viele Drucke hat der Token heute noch frei."""
        tok = self.data["tokens"].get(token)
        if not tok or not tok.get("active"):
            return 0
        today = self._today()
        used = int(tok.get("used", {}).get(today, 0))
        quota = int(tok.get("quota_per_day", 5))
        return max(0, quota - used)

    def validate(self, token: str) -> Optional[Dict[str, Any]]:
        """Prüft, ob Token existiert und aktiv ist."""
        tok = self.data["tokens"].get(token)
        if not tok or not tok.get("active"):
            return None
        return tok

    def consume(self, token: str) -> Optional[Dict[str, Any]]:
        """Verbraucht 1 Druckvorgang für heute."""
        tok = self.validate(token)
        if not tok:
            return None
        today = self._today()
        used = int(tok.setdefault("used", {}).get(today, 0))
        quota = int(tok.get("quota_per_day", 5))
        if used >= quota:
            return None
        tok["used"][today] = used + 1
        self._save()
        return tok


# ============================================================
# ==============  MONGODB-BACKEND (ATLAS)  ===================
# ============================================================

try:
    from pymongo import MongoClient, ReturnDocument
except ImportError:
    MongoClient = None
    ReturnDocument = None


class MongoGuestDB:
    """
    Token-Datenbank auf MongoDB-Basis (persistente Speicherung).
    API identisch zu GuestDB.
    """

    def __init__(self, uri: str, db_name: str = "printer", coll_name: str = "guest_tokens"):
        if MongoClient is None:
            raise RuntimeError("pymongo ist nicht installiert. Bitte in requirements.txt hinzufügen.")
        if not uri:
            raise RuntimeError("MONGO_URI fehlt in Environment Variables.")
        self.client = MongoClient(uri)
        self.coll = self.client[db_name][coll_name]
        self.coll.create_index("_id", unique=True)

    # ---------------------- Utilities -----------------------

    @staticmethod
    def _today() -> str:
        return time.strftime("%Y-%m-%d")

    @staticmethod
    def _now_ts() -> int:
        return int(time.time())

    # ---------------------- Public API ----------------------

    def create(self, name: str, quota_per_day: int = 5) -> str:
        token = secrets.token_urlsafe(24)
        doc = {
            "_id": token,
            "name": (name or "Gast").strip(),
            "created": self._now_ts(),
            "active": True,
            "quota_per_day": int(quota_per_day),
            "used": {}
        }
        self.coll.insert_one(doc)
        return token

    def revoke(self, token: str) -> bool:
        res = self.coll.update_one({"_id": token}, {"$set": {"active": False}})
        return res.matched_count > 0

    def list(self) -> List[Tuple[str, Dict[str, Any]]]:
        out = []
        for d in self.coll.find({}, projection={"_id": 1, "name": 1, "created": 1, "active": 1, "quota_per_day": 1}).sort("created", -1):
            token = d["_id"]
            info = {k: d.get(k) for k in ("name", "created", "active", "quota_per_day")}
            out.append((token, info))
        return out

    def remaining_today(self, token: str) -> int:
        d = self.coll.find_one({"_id": token, "active": True}, projection={"quota_per_day": 1, "used": 1})
        if not d:
            return 0
        today = self._today()
        used = int(d.get("used", {}).get(today, 0))
        quota = int(d.get("quota_per_day", 5))
        return max(0, quota - used)

    def validate(self, token: str) -> Optional[Dict[str, Any]]:
        d = self.coll.find_one({"_id": token, "active": True})
        if not d:
            return None
        return {
            "name": d.get("name", "Gast"),
            "created": d.get("created", 0),
            "active": True,
            "quota_per_day": d.get("quota_per_day", 5),
            "used": d.get("used", {})
        }

    def consume(self, token: str) -> Optional[Dict[str, Any]]:
        today = self._today()
        d = self.coll.find_one({"_id": token, "active": True})
        if not d:
            return None
        used = int(d.get("used", {}).get(today, 0))
        quota = int(d.get("quota_per_day", 5))
        if used >= quota:
            return None
        d2 = self.coll.find_one_and_update(
            {"_id": token, "active": True},
            {"$inc": {f"used.{today}": 1}},
            return_document=ReturnDocument.AFTER
        )
        if not d2:
            return None
        return {
            "name": d2.get("name", "Gast"),
            "created": d2.get("created", 0),
            "active": True,
            "quota_per_day": d2.get("quota_per_day", 5),
            "used": d2.get("used", {})
        }


# ============================================================
# ==============  AUTOMATISCHE BACKEND-WAHL  =================
# ============================================================

def get_guest_db() -> GuestDB | MongoGuestDB:
    """
    Wählt das passende Backend basierend auf der Umgebungsvariable GUEST_DB_BACKEND.
    - "mongo": benutzt MongoDB Atlas
    - "file":  lokale JSON-Datei (Default)
    """
    backend = os.getenv("GUEST_DB_BACKEND", "file").lower()
    if backend == "mongo":
        uri = os.getenv("MONGO_URI")
        db_name = os.getenv("MONGO_DB", "printer")
        coll_name = os.getenv("MONGO_COLL", "guest_tokens")
        return MongoGuestDB(uri, db_name, coll_name)
    else:
        path = os.getenv("GUEST_DB_FILE", "/data/guest_tokens.json")
        return GuestDB(path)