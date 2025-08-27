# guest_tokens.py
from __future__ import annotations
import os, json, time, secrets
from typing import Dict, Any, List, Tuple

class GuestDB:
    """
    Einfache Token-DB mit Tageskontingent.
    Datei-Format (JSON):
    {
      "tokens": {
        "<token>": {
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

    # --------- persistence ---------
    def _load(self):
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
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # --------- utils ---------
    @staticmethod
    def _today() -> str:
        return time.strftime("%Y-%m-%d")

    @staticmethod
    def _now_ts() -> int:
        return int(time.time())

    # --------- public API ---------
    def create(self, name: str, quota_per_day: int = 5) -> str:
        token = secrets.token_urlsafe(24)  # kurz & sicher
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
        tok = self.data["tokens"].get(token)
        if not tok: 
            return False
        tok["active"] = False
        self._save()
        return True

    def list(self) -> List[Tuple[str, Dict[str, Any]]]:
        # [(token, info), ...]
        return sorted(self.data["tokens"].items(), key=lambda kv: kv[1].get("created", 0), reverse=True)

    def remaining_today(self, token: str) -> int:
        tok = self.data["tokens"].get(token)
        if not tok or not tok.get("active"):
            return 0
        today = self._today()
        used = int(tok.get("used", {}).get(today, 0))
        return max(0, int(tok.get("quota_per_day", 5)) - used)

    def validate(self, token: str) -> Dict[str, Any] | None:
        tok = self.data["tokens"].get(token)
        if not tok or not tok.get("active"):
            return None
        return tok

    def consume(self, token: str) -> Dict[str, Any] | None:
        """Verbraucht 1 Sendung fuer heute, wenn noch verfuegbar. Gibt Token-Info zurueck."""
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
