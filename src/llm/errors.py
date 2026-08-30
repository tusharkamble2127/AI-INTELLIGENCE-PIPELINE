from __future__ import annotations


RETRYABLE_STATUS_CODES = {
    408,
    429,
    500,
    502,
    503,
    504,
}

NON_RETRYABLE_STATUS_CODES = {
    400,
    401,
    402,
    403,
    404,
}


def _extract_status_code(
    error: Exception,
) -> int | None:
    status_code = getattr(
        error,
        "status_code",
        None,
    )

    if isinstance(status_code, int):
        return status_code

    response = getattr(
        error,
        "response",
        None,
    )

    response_status = getattr(
        response,
        "status_code",
        None,
    )

    if isinstance(response_status, int):
        return response_status

    return None


def is_quota_exhausted(
    error: Exception,
) -> bool:
    """
    Detect provider quota/balance exhaustion.

    These conditions should NOT be retried repeatedly.

    Examples:
    - Gemini daily/free-tier quota
    - Groq tokens-per-day (TPD) exhaustion
    - explicit quota exceeded messages
    - insufficient account balance
    """

    message = str(error).lower()

    quota_indicators = (
        # Generic quota exhaustion
        "quota exceeded",
        "resource_exhausted",

        # Gemini
        "generaterequestsperdayperproject",
        "generaterequestsperminuteperproject",

        # Groq daily token quota
        "tokens per day (tpd)",
        "tokens per day",
        "token per day",

        # Account balance
        "insufficient balance",
    )

    return any(
        indicator in message
        for indicator in quota_indicators
    )


def is_retryable_error(
    error: Exception,
) -> bool:
    """
    Decide whether an LLM/provider error should
    be retried.

    Daily quota exhaustion and insufficient balance
    are NOT retryable.

    Temporary service failures and short-term rate
    limits remain retryable.
    """

    status_code = _extract_status_code(
        error
    )

    # Permanent quota/balance exhaustion.
    if is_quota_exhausted(error):
        return False

    if status_code in NON_RETRYABLE_STATUS_CODES:
        return False

    if status_code in RETRYABLE_STATUS_CODES:
        return True

    message = str(error).lower()

    # Short-term Groq rate limiting such as TPM.
    # Note: TPD is already handled above as non-retryable.
    if (
        "rate limit reached" in message
        or "rate_limit_exceeded" in message
    ):
        return True

    temporary_indicators = (
        "timeout",
        "temporarily unavailable",
        "service unavailable",
        "connection reset",
        "connection error",
    )

    if any(
        indicator in message
        for indicator in temporary_indicators
    ):
        return True

    return True