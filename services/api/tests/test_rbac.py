from app.core.security import hash_password, has_permission, verify_password
from app.models.enums import UserRole


def test_password_hash_roundtrip():
    hashed = hash_password("DemoPass123!")
    assert hashed != "DemoPass123!"
    assert verify_password("DemoPass123!", hashed)
    assert not verify_password("wrong", hashed)


def test_researcher_cannot_write_children():
    assert not has_permission(UserRole.RESEARCHER, "child:write")
    assert not has_permission(UserRole.RESEARCHER, "visit:write")
    assert has_permission(UserRole.RESEARCHER, "research:read")


def test_health_worker_can_register():
    assert has_permission(UserRole.HEALTH_WORKER, "child:write")
    assert has_permission(UserRole.HEALTH_WORKER, "predict:run")
    assert not has_permission(UserRole.HEALTH_WORKER, "model:activate")
