from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


def extract_retry_seconds(
    error: Exception,
    default: int = 300,
) -> int:
    """
    Extract a provider-supplied retry delay from
    an exception message.

    Supported examples:

        "retry in 1m49.296s"
        "retry in 44s"
        "retry in 57.946913251s"

    The returned cooldown is never shorter than
    the supplied default.
    """

    message = str(error).lower()

    # Example:
    # "Please try again in 1m49.296s"
    minute_match = re.search(
        r"retry in\s+(\d+)m\s*([\d.]+)s",
        message,
    )

    if minute_match:
        minutes = int(
            minute_match.group(1)
        )

        seconds = float(
            minute_match.group(2)
        )

        total_seconds = int(
            minutes * 60
            + seconds
            + 1
        )

        return max(
            default,
            total_seconds,
        )

    # Some providers use:
    # "retry in 44s"
    second_match = re.search(
        r"retry in\s+([\d.]+)s",
        message,
    )

    if second_match:
        seconds = float(
            second_match.group(1)
        )

        total_seconds = int(
            seconds + 1
        )

        return max(
            default,
            total_seconds,
        )

    # Some providers may say:
    # "Please try again in 90 seconds"
    plain_seconds_match = re.search(
        r"(?:retry|try again)\s+in\s+(\d+)\s+seconds?",
        message,
    )

    if plain_seconds_match:
        total_seconds = (
            int(
                plain_seconds_match.group(1)
            )
            + 1
        )

        return max(
            default,
            total_seconds,
        )

    return default


@dataclass
class ProviderState:
    """
    Tracks temporary provider availability.

    A provider can be temporarily disabled after
    quota exhaustion or another provider-specific
    failure.
    """

    disabled_until: datetime | None = None
    reason: str | None = None

    def is_available(self) -> bool:
        """
        Return True when the provider can be attempted.
        """

        if self.disabled_until is None:
            return True

        now = datetime.now(
            timezone.utc
        )

        if now >= self.disabled_until:
            self.disabled_until = None
            self.reason = None
            return True

        return False

    def disable(
        self,
        *,
        seconds: int,
        reason: str,
    ) -> None:
        """
        Temporarily disable the provider.
        """

        self.disabled_until = (
            datetime.now(
                timezone.utc
            )
            + timedelta(
                seconds=seconds
            )
        )

        self.reason = reason


class ProviderStateManager:
    """
    Keeps temporary availability state for
    all configured LLM providers.
    """

    def __init__(self) -> None:
        self._states: dict[
            str,
            ProviderState,
        ] = {}

    def get(
        self,
        provider_name: str,
    ) -> ProviderState:
        """
        Get or create the provider state.
        """

        if provider_name not in self._states:
            self._states[
                provider_name
            ] = ProviderState()

        return self._states[
            provider_name
        ]

    def disable(
        self,
        provider_name: str,
        *,
        seconds: int,
        reason: str,
    ) -> None:
        """
        Disable a provider temporarily.
        """

        self.get(
            provider_name
        ).disable(
            seconds=seconds,
            reason=reason,
        )

    def is_available(
        self,
        provider_name: str,
    ) -> bool:
        """
        Return whether the provider is currently
        available.
        """

        return self.get(
            provider_name
        ).is_available()