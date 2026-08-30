from __future__ import annotations

import asyncio
import logging

from dotenv import load_dotenv

from src.llm.orchestrator import (
    LLMOrchestrator,
)


logging.basicConfig(
    level=logging.INFO,
)


async def main() -> None:
    load_dotenv()

    orchestrator = LLMOrchestrator()

    prompt = """
You are testing an AI data extraction pipeline.

Reply with exactly:
LLM_TEST_OK
""".strip()

    result = await orchestrator.generate(
        prompt,
        max_tokens=20,
    )

    print("=" * 70)
    print("LLM ORCHESTRATOR TEST")
    print("=" * 70)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())