# sources/quote.py
import os
import random

# Optional: eigener Titel via ENV (sonst Standard)
TITLE = (os.getenv("QUOTE_TITLE") or "QUOTE OF THE DAY").strip() or "QUOTE OF THE DAY"

# Feste, wartungsfreie Liste (keine API-Abhaengigkeit)
QUOTES = [
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("What we think, we become.", "Buddha"),
    ("Well done is better than well said.", "Benjamin Franklin"),
    ("Simplicity is the ultimate sophistication.", "Leonardo da Vinci"),
    ("You miss 100% of the shots you don’t take.", "Wayne Gretzky"),
    ("Do what you can, with what you have, where you are.", "Theodore Roosevelt"),
    ("Action is the foundational key to all success.", "Pablo Picasso"),
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("The best way out is always through.", "Robert Frost"),
    ("If you want to go fast, go alone. If you want to go far, go together.", "African Proverb"),
    ("Discipline equals freedom.", "Jocko Willink"),
    ("Fortune favors the prepared mind.", "Louis Pasteur"),
]

def _pick() -> tuple[str, str]:
    text, author = random.choice(QUOTES)
    return text.strip(), (author or "Unknown").strip()

class Source:
    async def get_text(self):
        """
        Rueckgabe-Form wie in deinen Beispielen:
        - dict -> {"title": "...", "lines": ["..."]}

        routes_sources.py macht daraus PNG/Druck ohne Zeitstempel.
        """
        text, author = _pick()
        return {
            "title": TITLE,
            "lines": [f"“{text}”", f"— {author}"]
        }
