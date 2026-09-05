def token_cost_micro_usd(
    *,
    uncached_input_tokens: int,
    output_tokens: int,
    input_rate_micro_usd_per_million: int,
    output_rate_micro_usd_per_million: int,
) -> int:
    """Calculate uncached token cost, rounded up to the nearest microdollar."""
    values = (
        uncached_input_tokens,
        output_tokens,
        input_rate_micro_usd_per_million,
        output_rate_micro_usd_per_million,
    )
    if any(type(value) is not int for value in values):
        raise TypeError("Token counts and rates must be integers.")
    if any(value < 0 for value in values):
        raise ValueError("Token counts and rates must be nonnegative.")

    numerator = (
        uncached_input_tokens * input_rate_micro_usd_per_million
        + output_tokens * output_rate_micro_usd_per_million
    )
    return (numerator + 999_999) // 1_000_000