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

    # Simulate Gemini + Groq being unavailable.
    orchestrator.state.disable(
        "gemini",
        seconds=600,
        reason="simulated Gemini quota exhaustion",
    )

    orchestrator.state.disable(
        "groq",
        seconds=600,
        reason="simulated Groq quota exhaustion",
    )

    print("=" * 70)
    print("DEEPSEEK FALLBACK TEST")
    print("=" * 70)

    result = await orchestrator.generate(
        "Reply with exactly: "
        "DEEPSEEK_FALLBACK_OK",
        max_tokens=50,
    )

    print()
    print("Result:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())