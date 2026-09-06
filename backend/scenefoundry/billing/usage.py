from scenefoundry.billing.cost import token_cost_micro_usd
from scenefoundry.billing.rates import TokenRateCard


def price_director_usage(
    records: list[dict[str, object]],
    *,
    model: str,
    location: str,
    rate: TokenRateCard,
) -> int:
    """Price one uncached director response with complete token evidence."""
    if model != rate.model or location != rate.location:
        raise ValueError("Rate card does not match the generation.")
    if rate.service_tier != "standard":
        raise ValueError("Only standard service pricing is supported.")
    if len(records) != 1:
        raise ValueError("Expected exactly one director usage record.")

    usage = records[0]
    if usage.get("traffic_type") != "ON_DEMAND":
        raise ValueError("Unsupported or missing traffic type.")
    if usage.get("cached_content_token_count", 0) != 0:
        raise ValueError("Cached usage requires separate pricing.")

    fields = (
        "prompt_token_count",
        "candidates_token_count",
        "thoughts_token_count",
        "total_token_count",
    )
    counts = [usage.get(field) for field in fields]
    if any(type(count) is not int or count < 0 for count in counts):
        raise ValueError("Token counts are missing or invalid.")

    prompt, response, reasoning, total = counts
    if prompt + response + reasoning != total:
        raise ValueError("Token categories do not reconcile with the total.")

    return token_cost_micro_usd(
        uncached_input_tokens=prompt,
        output_tokens=response + reasoning,
        input_rate_micro_usd_per_million=rate.input_rate_micro_usd_per_million,
        output_rate_micro_usd_per_million=rate.output_rate_micro_usd_per_million,
    )