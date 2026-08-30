from __future__ import annotations

import asyncio
import logging

from dotenv import load_dotenv

from src.llm.orchestrator import LLMOrchestrator


logging.basicConfig(
    level=logging.INFO,
)


async def main() -> None:
    load_dotenv()

    orchestrator = LLMOrchestrator()

    # Simulate Gemini quota exhaustion.
    orchestrator.state.disable(
        "gemini",
        seconds=300,
        reason="simulated quota exhaustion",
    )

    print("=" * 70)
    print("LLM ORCHESTRATOR STATE TEST")
    print("=" * 70)

    print()
    print("First request:")

    result_1 = await orchestrator.generate(
        "Reply with exactly: STATE_TEST_OK",
        max_tokens=100,
    )

    print()
    print("Result 1:")
    print(result_1)

    print()
    print("Second request:")

    result_2 = await orchestrator.generate(
        "Reply with exactly: STATE_TEST_OK",
        max_tokens=100,
    )

    print()
    print("Result 2:")
    print(result_2)


if __name__ == "__main__":
    asyncio.run(main())