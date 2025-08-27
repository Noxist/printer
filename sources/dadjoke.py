import httpx

UA = "Leandros-Printer/1.0 (+https://icanhazdadjoke.com/)"
TIMEOUT = 10.0

class Source:
    async def get_text(self) -> str:
        headers = {"Accept": "text/plain", "User-Agent": UA}
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get("https://icanhazdadjoke.com/", headers=headers)
            r.raise_for_status()
            return (r.text or "").strip()
