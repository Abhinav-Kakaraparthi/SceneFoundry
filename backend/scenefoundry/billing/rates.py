from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TokenRateCard(BaseModel):
    """A dated pricing snapshot for uncached input and text output."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    rate_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    location: str = Field(min_length=1)
    service_tier: str = Field(min_length=1)
    observed_on: date
    source_url: str = Field(min_length=1)
    input_rate_micro_usd_per_million: int = Field(ge=0)
    output_rate_micro_usd_per_million: int = Field(ge=0)


GEMINI_35_FLASH_GLOBAL_STANDARD = TokenRateCard(
    rate_id="gemini-3.5-flash_global_standard_2026-09-05",
    model="gemini-3.5-flash",
    location="global",
    service_tier="standard",
    observed_on=date(2026, 9, 5),
    source_url=(
        "https://cloud.google.com/gemini-enterprise-agent-platform/"
        "generative-ai/pricing"
    ),
    input_rate_micro_usd_per_million=1_500_000,
    output_rate_micro_usd_per_million=9_000_000,
)