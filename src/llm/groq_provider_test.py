from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from src.llm.groq_provider import GroqProvider


async def main() -> None:
    load_dotenv()

    provider = GroqProvider()

    result = await provider.generate(
        "Reply with exactly: GROQ_PROVIDER_OK",
        max_tokens=100,
    )

    print("=" * 70)
    print("GROQ PROVIDER TEST")
    print("=" * 70)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())