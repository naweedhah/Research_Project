from __future__ import annotations

from app.core.deps import CurrentUser
from app.models.enums import UserRole
from app.models.identity import User
from app.models.paediatric import Child


def facility_scope_ids(user: CurrentUser) -> list[str] | None:
    """None means unrestricted (system admin). Researcher is scoped to own facility de-identified."""
    if user.role == UserRole.SYSTEM_ADMIN:
        return None
    return [user.facility_id]


def assert_child_access(user: CurrentUser, child: Child) -> None:
    from fastapi import HTTPException, status

    if user.role == UserRole.SYSTEM_ADMIN:
        return
    if user.role == UserRole.RESEARCHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Researchers may not access identifiable child records",
        )
    if str(child.facility_id) != user.facility_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
