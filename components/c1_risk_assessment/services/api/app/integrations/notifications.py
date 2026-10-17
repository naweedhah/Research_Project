from __future__ import annotations

from abc import ABC, abstractmethod


class NotificationProvider(ABC):
    @abstractmethod
    def send(self, *, to: str, title: str, body: str) -> dict: ...


class MockNotificationProvider(NotificationProvider):
    def send(self, *, to: str, title: str, body: str) -> dict:
        return {"delivered": False, "provider": "mock", "to": to, "title": title}


class EmailNotificationProvider(NotificationProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def send(self, *, to: str, title: str, body: str) -> dict:
        if not self.api_key:
            return MockNotificationProvider().send(to=to, title=title, body=body)
        raise RuntimeError("Live email sending is disabled unless explicitly configured in a non-demo environment")


class SmsNotificationProvider(NotificationProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def send(self, *, to: str, title: str, body: str) -> dict:
        if not self.api_key:
            return MockNotificationProvider().send(to=to, title=title, body=body)
        raise RuntimeError("Live SMS sending is disabled unless explicitly configured in a non-demo environment")


def get_provider() -> NotificationProvider:
    from app.core.config import get_settings

    settings = get_settings()
    if settings.notification_provider == "email" and settings.email_api_key:
        return EmailNotificationProvider(settings.email_api_key)
    if settings.notification_provider == "sms" and settings.sms_api_key:
        return SmsNotificationProvider(settings.sms_api_key)
    return MockNotificationProvider()
