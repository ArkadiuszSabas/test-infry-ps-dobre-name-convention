"""Framework-free document approval workflow contracts."""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum


class DocumentApprovalDecision(StrEnum):
    """An immutable decision recorded in an approval run."""

    APPROVED = "approved"
    REJECTED = "rejected"


class DocumentApprovalStepStatus(StrEnum):
    """The current state of one required approval step."""

    WAITING = "waiting"
    APPROVED = "approved"


class DocumentApprovalWorkflowStatus(StrEnum):
    """Aggregate state exposed to review and Inbox clients."""

    WAITING_FOR_REVIEW = "waiting_for_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"


class DocumentApprovalWorkflowError(ValueError):
    """A business invariant prevented an approval transition."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class DocumentApprovalStep:
    """One current-run approval step and its immutable decision details."""

    number: int
    status: DocumentApprovalStepStatus
    reviewer_actor_id: str | None = None
    decided_at: datetime | None = None
    comment: str | None = None
    reviewer_display_name: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentApprovalDecisionRecord:
    """An append-only decision record retained across reset runs."""

    run_number: int
    step_number: int
    decision: DocumentApprovalDecision
    actor_id: str
    comment: str | None
    decided_at: datetime
    actor_display_name: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentApprovalWorkflow:
    """Current approval workflow plus its immutable decision history."""

    run_number: int
    status: DocumentApprovalWorkflowStatus
    steps: tuple[DocumentApprovalStep, ...]
    history: tuple[DocumentApprovalDecisionRecord, ...]
    review_version: int = 1
    required_approvals: int = 2

    def __post_init__(self) -> None:
        if isinstance(self.required_approvals, bool) or self.required_approvals not in (
            1,
            2,
        ):
            raise ValueError("Document approval requires one or two reviewers.")
        if len(self.steps) != self.required_approvals:
            raise ValueError("Document approval steps must match required approvals.")

    @property
    def completed_at(self) -> datetime | None:
        """Return the timestamp of the final approval when complete."""

        if self.status is not DocumentApprovalWorkflowStatus.APPROVED:
            return None
        return self.steps[-1].decided_at

    def is_actor_active(self, actor_id: str) -> bool:
        """Return whether an eligible actor can decide the current workflow step."""

        current = next(
            (step for step in self.steps if step.status is DocumentApprovalStepStatus.WAITING), None
        )
        if current is None:
            return False
        prior_reviewer_ids = {
            step.reviewer_actor_id
            for step in self.steps
            if step.number < current.number and step.reviewer_actor_id is not None
        }
        return actor_id not in prior_reviewer_ids

    def decide(
        self,
        *,
        actor_id: str,
        decision: DocumentApprovalDecision,
        comment: str | None,
        decided_at: datetime,
    ) -> tuple[DocumentApprovalDecisionRecord, DocumentApprovalWorkflow]:
        """Apply one decision without performing persistence."""

        if decision is DocumentApprovalDecision.REJECTED and (
            comment is None or not comment.strip()
        ):
            raise DocumentApprovalWorkflowError(
                code="DOCUMENT_APPROVAL_REJECT_REASON_REQUIRED",
                message="A rejection reason is required.",
            )
        waiting = next(
            (step for step in self.steps if step.status is DocumentApprovalStepStatus.WAITING),
            None,
        )
        if waiting is None:
            raise DocumentApprovalWorkflowError(
                code="DOCUMENT_APPROVAL_WORKFLOW_COMPLETE",
                message="The document approval workflow is already complete.",
            )
        if not self.is_actor_active(actor_id):
            raise DocumentApprovalWorkflowError(
                code="DOCUMENT_APPROVAL_SECOND_REVIEWER_MUST_DIFFER",
                message="Each approval requires a different reviewer.",
            )
        record = DocumentApprovalDecisionRecord(
            run_number=self.run_number,
            step_number=waiting.number,
            decision=decision,
            actor_id=actor_id,
            comment=comment,
            decided_at=decided_at,
        )
        if decision is DocumentApprovalDecision.REJECTED:
            return record, DocumentApprovalWorkflow(
                run_number=self.run_number + 1,
                status=DocumentApprovalWorkflowStatus.WAITING_FOR_REVIEW,
                steps=tuple(
                    DocumentApprovalStep(number, DocumentApprovalStepStatus.WAITING)
                    for number in range(1, self.required_approvals + 1)
                ),
                history=(*self.history, record),
                review_version=self.review_version,
                required_approvals=self.required_approvals,
            )
        approved_step = replace(
            waiting,
            status=DocumentApprovalStepStatus.APPROVED,
            reviewer_actor_id=actor_id,
            decided_at=decided_at,
            comment=comment,
        )
        steps = tuple(
            approved_step if step.number == waiting.number else step for step in self.steps
        )
        complete = all(step.status is DocumentApprovalStepStatus.APPROVED for step in steps)
        return record, DocumentApprovalWorkflow(
            run_number=self.run_number,
            status=(
                DocumentApprovalWorkflowStatus.APPROVED
                if complete
                else DocumentApprovalWorkflowStatus.IN_REVIEW
            ),
            steps=steps,
            history=(*self.history, record),
            review_version=self.review_version,
            required_approvals=self.required_approvals,
        )
