"""Tests for the Hush storage module."""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.hush.const import Category
from custom_components.hush.storage import NotificationStore


@pytest.fixture
async def store(tmp_storage_path: Path, mock_hass) -> NotificationStore:
    """Create a test notification store."""
    store = NotificationStore(mock_hass, tmp_storage_path)
    await store.async_initialize()
    yield store
    await store.async_close()


class TestNotificationStore:
    """Tests for NotificationStore."""

    @pytest.mark.asyncio
    async def test_initialize_creates_database(
        self, store: NotificationStore, tmp_storage_path: Path
    ) -> None:
        """Test that initialization creates the database."""
        db_path = tmp_storage_path / "notifications.db"
        assert db_path.exists()

    @pytest.mark.asyncio
    async def test_add_notification(self, store: NotificationStore) -> None:
        """Test adding a notification."""
        notification_id = await store.async_add_notification(
            message="Test message",
            title="Test title",
            category=Category.INFO,
            entity_id="sensor.test",
            delivered=True,
        )
        assert notification_id
        assert len(notification_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_get_recent_empty(self, store: NotificationStore) -> None:
        """Test getting recent notifications when empty."""
        notifications = await store.async_get_recent()
        assert notifications == []

    @pytest.mark.asyncio
    async def test_get_recent_with_notifications(self, store: NotificationStore) -> None:
        """Test getting recent notifications."""
        await store.async_add_notification(message="First", category=Category.INFO)
        await store.async_add_notification(message="Second", category=Category.SAFETY)

        notifications = await store.async_get_recent()
        assert len(notifications) == 2
        # Most recent first
        assert notifications[0].message == "Second"
        assert notifications[1].message == "First"

    @pytest.mark.asyncio
    async def test_get_recent_respects_limit(self, store: NotificationStore) -> None:
        """Test that get_recent respects the limit parameter."""
        for i in range(10):
            await store.async_add_notification(message=f"Message {i}", category=Category.INFO)

        notifications = await store.async_get_recent(limit=5)
        assert len(notifications) == 5

    @pytest.mark.asyncio
    async def test_notification_record_to_dict(self, store: NotificationStore) -> None:
        """Test NotificationRecord.to_dict()."""
        await store.async_add_notification(
            message="Test",
            title="Title",
            category=Category.SAFETY,
            entity_id="binary_sensor.smoke",
            delivered=True,
        )

        notifications = await store.async_get_recent(limit=1)
        record_dict = notifications[0].to_dict()

        assert "id" in record_dict
        assert "timestamp" in record_dict
        assert record_dict["message"] == "Test"
        assert record_dict["title"] == "Title"
        assert record_dict["category"] == "safety"
        assert record_dict["entity_id"] == "binary_sensor.smoke"
        assert record_dict["delivered"] is True
        assert record_dict["collapsed_count"] == 1

    @pytest.mark.asyncio
    async def test_get_today_stats_empty(self, store: NotificationStore) -> None:
        """Test getting today's stats when empty."""
        stats = await store.async_get_today_stats()
        assert stats["total"] == 0
        assert stats["safety_count"] == 0
        assert stats["delivered_count"] == 0

    @pytest.mark.asyncio
    async def test_get_today_stats(self, store: NotificationStore) -> None:
        """Test getting today's stats."""
        await store.async_add_notification(message="Info 1", category=Category.INFO, delivered=True)
        await store.async_add_notification(
            message="Info 2", category=Category.INFO, delivered=False
        )
        await store.async_add_notification(
            message="Safety", category=Category.SAFETY, delivered=True
        )

        stats = await store.async_get_today_stats()
        assert stats["total"] == 3
        assert stats["safety_count"] == 1
        assert stats["delivered_count"] == 2


class TestDeduplication:
    """Tests for notification deduplication."""

    @pytest.mark.asyncio
    async def test_is_duplicate_no_match(self, store: NotificationStore) -> None:
        """Test is_duplicate when no duplicate exists."""
        is_dup = await store.async_is_duplicate("New message", window_minutes=5)
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_is_duplicate_match(self, store: NotificationStore) -> None:
        """Test is_duplicate when duplicate exists."""
        await store.async_add_notification(message="Duplicate me", category=Category.INFO)

        is_dup = await store.async_is_duplicate("Duplicate me", window_minutes=5)
        assert is_dup is True

    @pytest.mark.asyncio
    async def test_is_duplicate_different_message(self, store: NotificationStore) -> None:
        """Test is_duplicate with different message."""
        await store.async_add_notification(message="Original", category=Category.INFO)

        is_dup = await store.async_is_duplicate("Different", window_minutes=5)
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_is_duplicate_increments_collapsed_count(self, store: NotificationStore) -> None:
        """Test that is_duplicate increments collapsed_count."""
        await store.async_add_notification(message="Repeat me", category=Category.INFO)

        # Check duplicate twice
        await store.async_is_duplicate("Repeat me", window_minutes=5)
        await store.async_is_duplicate("Repeat me", window_minutes=5)

        notifications = await store.async_get_recent(limit=1)
        assert notifications[0].collapsed_count == 3  # Original + 2 duplicates
