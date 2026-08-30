from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from src.llm.deepseek_provider import (
    DeepSeekProvider,
)


async def main() -> None:
    load_dotenv()

    provider = DeepSeekProvider()

    result = await provider.generate(
        "Reply with exactly: "
        "NVIDIA_DEEPSEEK_OK",
        max_tokens=30,
    )

    print("=" * 70)
    print("NVIDIA DEEPSEEK PROVIDER TEST")
    print("=" * 70)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())