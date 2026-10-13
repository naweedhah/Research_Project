"""Model registry (spec §13, §15): separates the active/reference model from candidates.

C3 never overwrites the active model directly — it always promotes a verified
candidate or rejects it and retains what's currently active.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from component3.interfaces import ModelArtifact
from component3.verify.verify import VerificationResult


@dataclass(frozen=True)
class HistoryEntry:
    version: str
    action: str  # "initial" | "promoted" | "rejected" | "rollback"
    parent_version: str | None
    timestamp: datetime
    verification: VerificationResult | None = None
    reason: str | None = None


class ModelRegistry:
    def __init__(self, initial_model: ModelArtifact):
        self._active = initial_model
        self._promoted_stack: list[ModelArtifact] = [initial_model]
        self._history: list[HistoryEntry] = [
            HistoryEntry(
                version=initial_model.version,
                action="initial",
                parent_version=None,
                timestamp=datetime.now(timezone.utc),
            )
        ]

    @property
    def active_model(self) -> ModelArtifact:
        return self._active

    @property
    def history(self) -> tuple[HistoryEntry, ...]:
        return tuple(self._history)

    def promote(self, candidate: ModelArtifact, verification: VerificationResult | None = None) -> None:
        self._active = candidate
        self._promoted_stack.append(candidate)
        self._history.append(
            HistoryEntry(
                version=candidate.version,
                action="promoted",
                parent_version=candidate.metadata.parent_version,
                timestamp=datetime.now(timezone.utc),
                verification=verification,
            )
        )

    def reject(self, candidate: ModelArtifact, verification: VerificationResult | None = None, reason: str | None = None) -> None:
        self._history.append(
            HistoryEntry(
                version=candidate.version,
                action="rejected",
                parent_version=candidate.metadata.parent_version,
                timestamp=datetime.now(timezone.utc),
                verification=verification,
                reason=reason,
            )
        )

    def rollback(self) -> ModelArtifact:
        if len(self._promoted_stack) <= 1:
            raise ValueError("no prior promoted model to roll back to")
        rolled_back_from = self._promoted_stack.pop()
        self._active = self._promoted_stack[-1]
        self._history.append(
            HistoryEntry(
                version=self._active.version,
                action="rollback",
                parent_version=rolled_back_from.version,
                timestamp=datetime.now(timezone.utc),
            )
        )
        return self._active
