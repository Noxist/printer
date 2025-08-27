from typing import Protocol

class TextSource(Protocol):
    async def get_text(self) -> str: ...
