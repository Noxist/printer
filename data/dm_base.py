# sources/dm_base.py
import random
from typing import Literal, Dict, Any
from .dm_data import DM_PASSAGES

Lang = Literal["en", "de", "both"]

def pick_random() -> Dict[str, Any]:
    return random.choice(DM_PASSAGES)

def format_dm(lang: Lang) -> Dict[str, list[str]]:
    item = pick_random()
    ref_en, ref_de = item["ref_en"], item["ref_de"]
    txt_en, txt_de = item["en"].strip(), item["de"].strip()

    if lang == "en":
        return {"title": ref_en, "lines": [f"“{txt_en}”"]}
    if lang == "de":
        return {"title": ref_de, "lines": [f"„{txt_de}“"]}
    return {
        "title": f"{ref_en}  /  {ref_de}",
        "lines": [
            f"EN: “{txt_en}”",
            "",
            f"DE: „{txt_de}“",
        ],
    }
