# sources/dm_both.py
from .dm_base import format_dm

class Source:
    async def get_text(self):
        return format_dm("both")
