from __future__ import annotations

import os
import asyncio

from groq import AsyncGroq
from dotenv import load_dotenv


async def main() -> None:
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing from .env"
        )

    client = AsyncGroq(
        api_key=api_key
    )

    models = await client.models.list()

    print("=" * 70)
    print("GROQ AVAILABLE MODELS")
    print("=" * 70)

    for model in models.data:
        print(model.id)


if __name__ == "__main__":
    asyncio.run(main())