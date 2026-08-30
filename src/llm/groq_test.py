from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from src.llm.groq_provider import GroqProvider


async def main() -> None:
    load_dotenv()

    provider = GroqProvider()

    print("=" * 70)
    print("GROQ RAW RESPONSE TEST")
    print("=" * 70)

    # Directly call the SDK here so we can inspect
    # the actual response structure.
    response = await provider.client.chat.completions.create(
        model=provider.model,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: GROQ_TEST_OK",
            }
        ],
        max_tokens=50,
        include_reasoning=False,
    )

    print("Model:")
    print(response.model)

    print("\nChoices:")
    print(len(response.choices))

    for index, choice in enumerate(
        response.choices,
        start=1,
    ):
        print(f"\nChoice {index}")
        print(f"finish_reason: {choice.finish_reason}")
        print(f"message role : {choice.message.role}")
        print(f"content      : {repr(choice.message.content)}")

        reasoning = getattr(
            choice.message,
            "reasoning",
            None,
        )

        print(
            f"reasoning    : {repr(reasoning)}"
        )

        tool_calls = getattr(
            choice.message,
            "tool_calls",
            None,
        )

        print(
            f"tool_calls   : {repr(tool_calls)}"
        )

    print("\nUsage:")
    print(response.usage)


if __name__ == "__main__":
    asyncio.run(main())