import asyncio
import json

import httpx

USER_ID = "bae55d8e-ba28-4c0f-94bc-b69aa551b3fc"
URL = "http://127.0.0.1:8000/debug/availabilities/punctual"


async def post(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(URL, json=payload)
        r.raise_for_status()
        return r.json()


async def main() -> None:
    payload1 = {
        "user_id": USER_ID,
        "start_time_utc": "2026-01-30T10:30:00+00:00",
        "end_time_utc": "2026-01-30T11:30:00+00:00",
        "timezone": "Europe/Madrid",
        "source": "punctual",
    }

    payload2 = {
        "user_id": USER_ID,
        "start_time_utc": "2026-01-30T10:45:00+00:00",
        "end_time_utc": "2026-01-30T11:15:00+00:00",
        "timezone": "Europe/Madrid",
        "source": "punctual",
    }

    results = await asyncio.gather(post(payload1), post(payload2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
