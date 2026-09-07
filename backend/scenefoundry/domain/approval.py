from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


ApprovalDecision = Literal["approved", "changes_requested"]


class RevisionApproval(BaseModel):
    """One immutable human decision for one immutable scene revision."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    revision_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    decision: ApprovalDecision
    reviewer_id: str = Field(
        min_length=1,
        max_length=200,
        pattern=r"^\S+$",
    )
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_change_note(self) -> Self:
        if self.decision == "changes_requested" and not self.note:
            raise ValueError(
                "A review note is required when requesting changes."
            )
        return self


def require_approved_revision(
    revision_id: str,
    approval: RevisionApproval | None,
) -> None:
    """Block production unless the exact revision has human approval."""

    if approval is None:
        raise ValueError("Scene revision is awaiting director approval.")
    if approval.revision_id != revision_id:
        raise ValueError("Approval does not match the scene revision.")
    if approval.decision != "approved":
        raise ValueError("Scene revision requires changes.")
