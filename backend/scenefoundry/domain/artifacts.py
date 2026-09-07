from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ArtifactKind = Literal[
    "creative_brief",
    "script",
    "cast_bible",
    "style_bible",
    "shot_plan",
    "layout_preview",
    "motion_preview",
    "cinematic_clip",
    "review_evidence",
    "review_cut",
    "sound_mix",
    "delivery_cut",
]

ARTIFACT_ORDER: tuple[ArtifactKind, ...] = (
    "creative_brief",
    "script",
    "cast_bible",
    "style_bible",
    "shot_plan",
    "layout_preview",
    "motion_preview",
    "cinematic_clip",
    "review_evidence",
    "review_cut",
    "sound_mix",
    "delivery_cut",
)

DEPENDENTS: dict[ArtifactKind, frozenset[ArtifactKind]] = {
    "creative_brief": frozenset({"script", "style_bible"}),
    "script": frozenset({"cast_bible", "shot_plan"}),
    "cast_bible": frozenset({"shot_plan", "cinematic_clip"}),
    "style_bible": frozenset({"layout_preview", "cinematic_clip"}),
    "shot_plan": frozenset(
        {"layout_preview", "motion_preview", "cinematic_clip"}
    ),
    "layout_preview": frozenset({"motion_preview", "review_evidence"}),
    "motion_preview": frozenset({"review_evidence"}),
    "cinematic_clip": frozenset({"review_evidence", "review_cut"}),
    "review_evidence": frozenset({"review_cut"}),
    "review_cut": frozenset({"sound_mix"}),
    "sound_mix": frozenset({"delivery_cut"}),
    "delivery_cut": frozenset(),
}


def impacted_artifacts(
    changed: set[ArtifactKind] | frozenset[ArtifactKind],
) -> tuple[ArtifactKind, ...]:
    """Return changed artifacts and every transitively dependent artifact."""
    unknown = set(changed) - set(ARTIFACT_ORDER)
    if unknown:
        raise ValueError(f"Unknown artifact kinds: {sorted(unknown)}")

    impacted: set[ArtifactKind] = set(changed)
    pending = list(changed)

    while pending:
        current = pending.pop()
        for dependent in DEPENDENTS[current]:
            if dependent not in impacted:
                impacted.add(dependent)
                pending.append(dependent)

    return tuple(kind for kind in ARTIFACT_ORDER if kind in impacted)


class ArtifactInput(BaseModel):
    """One immutable upstream artifact used to produce another artifact."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    artifact_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    kind: ArtifactKind
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ArtifactStamp(BaseModel):
    """Provenance attached to every generated production artifact."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    artifact_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    kind: ArtifactKind
    revision_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    scope_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    inputs: tuple[ArtifactInput, ...] = Field(default=(), strict=False)
    uri: str | None = Field(default=None, max_length=2000)
