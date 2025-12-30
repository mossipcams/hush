"""SQLite storage for Hush notification history."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiosqlite

from .const import DB_NAME, Category

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class NotificationRecord:
    """A stored notification record."""

    def __init__(
        self,
        id: str,
        timestamp: datetime,
        message: str,
        title: str | None,
        category: Category,
        entity_id: str | None,
        delivered: bool,
        collapsed_count: int,
    ) -> None:
        """Initialize a notification record."""
        self.id = id
        self.timestamp = timestamp
        self.message = message
        self.title = title
        self.category = category
        self.entity_id = entity_id
        self.delivered = delivered
        self.collapsed_count = collapsed_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "title": self.title,
            "category": self.category.value,
            "entity_id": self.entity_id,
            "delivered": self.delivered,
            "collapsed_count": self.collapsed_count,
        }


class NotificationStore:
    """Async SQLite storage for notification history."""

    def __init__(self, hass: HomeAssistant, storage_path: Path) -> None:
        """Initialize the notification store."""
        self._hass = hass
        self._storage_path = storage_path
        self._db_path = storage_path / DB_NAME
        self._db: aiosqlite.Connection | None = None

    async def async_initialize(self) -> None:
        """Initialize the database."""
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row

        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                message TEXT NOT NULL,
                title TEXT,
                category TEXT NOT NULL DEFAULT 'info',
                entity_id TEXT,
                delivered INTEGER NOT NULL DEFAULT 1,
                collapsed_count INTEGER NOT NULL DEFAULT 1
            )
        """)

        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON notifications(timestamp DESC)
        """)

        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_message_timestamp ON notifications(message, timestamp)
        """)

        await self._db.commit()
        _LOGGER.debug("Notification database initialized at %s", self._db_path)

    async def async_close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def async_add_notification(
        self,
        message: str,
        title: str | None = None,
        category: Category = Category.INFO,
        entity_id: str | None = None,
        delivered: bool = True,
    ) -> str:
        """Add a notification to the store.

        Returns the notification ID.
        """
        if not self._db:
            raise RuntimeError("Database not initialized")

        notification_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC).isoformat()

        await self._db.execute(
            """
            INSERT INTO notifications (id, timestamp, message, title, category, entity_id, delivered, collapsed_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (notification_id, timestamp, message, title, category.value, entity_id, int(delivered)),
        )
        await self._db.commit()

        # Cleanup old notifications (keep last 7 days)
        await self._async_cleanup_old()

        return notification_id

    async def async_get_recent(self, limit: int = 50) -> list[NotificationRecord]:
        """Get recent notifications."""
        if not self._db:
            raise RuntimeError("Database not initialized")

        cursor = await self._db.execute(
            """
            SELECT id, timestamp, message, title, category, entity_id, delivered, collapsed_count
            FROM notifications
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = await cursor.fetchall()
        return [self._row_to_record(row) for row in rows]

    async def async_get_today_stats(self) -> dict[str, int]:
        """Get notification statistics for today."""
        if not self._db:
            raise RuntimeError("Database not initialized")

        today_start = (
            datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        )

        cursor = await self._db.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN category = 'safety' THEN 1 ELSE 0 END) as safety_count,
                SUM(CASE WHEN delivered = 1 THEN 1 ELSE 0 END) as delivered_count
            FROM notifications
            WHERE timestamp >= ?
            """,
            (today_start,),
        )

        row = await cursor.fetchone()
        if row is None:
            return {"total": 0, "safety_count": 0, "delivered_count": 0}
        return {
            "total": row["total"] or 0,
            "safety_count": row["safety_count"] or 0,
            "delivered_count": row["delivered_count"] or 0,
        }

    async def async_is_duplicate(self, message: str, window_minutes: int = 5) -> bool:
        """Check if a similar message was sent recently.

        If duplicate found, increments the collapsed_count of the existing record.
        """
        if not self._db:
            raise RuntimeError("Database not initialized")

        cutoff = (datetime.now(UTC) - timedelta(minutes=window_minutes)).isoformat()

        cursor = await self._db.execute(
            """
            SELECT id, collapsed_count
            FROM notifications
            WHERE message = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (message, cutoff),
        )

        row = await cursor.fetchone()
        if row:
            # Increment collapsed count
            await self._db.execute(
                """
                UPDATE notifications
                SET collapsed_count = collapsed_count + 1
                WHERE id = ?
                """,
                (row["id"],),
            )
            await self._db.commit()
            return True

        return False

    async def _async_cleanup_old(self, days: int = 7) -> None:
        """Remove notifications older than the specified days."""
        if not self._db:
            return

        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()

        await self._db.execute(
            """
            DELETE FROM notifications
            WHERE timestamp < ?
            """,
            (cutoff,),
        )
        await self._db.commit()

    def _row_to_record(self, row: aiosqlite.Row) -> NotificationRecord:
        """Convert a database row to a NotificationRecord."""
        return NotificationRecord(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            message=row["message"],
            title=row["title"],
            category=Category(row["category"]),
            entity_id=row["entity_id"],
            delivered=bool(row["delivered"]),
            collapsed_count=row["collapsed_count"],
        )
