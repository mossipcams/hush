"""Constants for the Hush integration."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from re import Pattern

DOMAIN: Final = "hush"

# Config keys
CONF_DELIVERY_TARGET: Final = "delivery_target"
CONF_QUIET_HOURS_ENABLED: Final = "quiet_hours_enabled"
CONF_QUIET_HOURS_START: Final = "quiet_hours_start"
CONF_QUIET_HOURS_END: Final = "quiet_hours_end"
CONF_CATEGORY_BEHAVIORS: Final = "category_behaviors"
CONF_ENTITY_OVERRIDES: Final = "entity_overrides"

# Default values
DEFAULT_QUIET_HOURS_ENABLED: Final = True
DEFAULT_QUIET_HOURS_START: Final = "22:00"
DEFAULT_QUIET_HOURS_END: Final = "07:00"
DEFAULT_DEDUP_WINDOW_MINUTES: Final = 5
DEFAULT_DEVICE_DEDUP_WINDOW_MINUTES: Final = 60

# Storage
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}.config"
DB_NAME: Final = "notifications.db"


class Category(StrEnum):
    """Notification categories with smart defaults."""

    SAFETY = "safety"
    SECURITY = "security"
    DEVICE = "device"
    MOTION = "motion"
    INFO = "info"


class CategoryBehavior(StrEnum):
    """Behavior options for each category."""

    ALWAYS_NOTIFY = "always_notify"
    NOTIFY_RESPECT_QUIET = "notify_respect_quiet"
    NOTIFY_ONCE_PER_HOUR = "notify_once_per_hour"
    LOG_ONLY = "log_only"
    NOTIFY_WITH_DEDUP = "notify_with_dedup"


# Default behavior per category
DEFAULT_CATEGORY_BEHAVIORS: dict[Category, CategoryBehavior] = {
    Category.SAFETY: CategoryBehavior.ALWAYS_NOTIFY,
    Category.SECURITY: CategoryBehavior.NOTIFY_RESPECT_QUIET,
    Category.DEVICE: CategoryBehavior.NOTIFY_ONCE_PER_HOUR,
    Category.MOTION: CategoryBehavior.LOG_ONLY,
    Category.INFO: CategoryBehavior.NOTIFY_WITH_DEDUP,
}

# Category display info
CATEGORY_ICONS: dict[Category, str] = {
    Category.SAFETY: "🚨",
    Category.SECURITY: "🚪",
    Category.DEVICE: "📱",
    Category.MOTION: "👤",
    Category.INFO: "ℹ️",
}

CATEGORY_NAMES: dict[Category, str] = {
    Category.SAFETY: "Safety",
    Category.SECURITY: "Security",
    Category.DEVICE: "Device",
    Category.MOTION: "Motion",
    Category.INFO: "Other",
}

# Classification patterns (entity_id substring -> category)
# Legacy pattern sets (kept for backwards compatibility)
SAFETY_PATTERNS: Final = frozenset(
    {"smoke", "co2", "carbon", "leak", "flood", "water_sensor", "gas"}
)
SECURITY_PATTERNS: Final = frozenset({"door", "window", "lock", "alarm", "siren", "garage"})
DEVICE_PATTERNS: Final = frozenset({"battery", "offline", "unavailable", "connectivity"})
MOTION_PATTERNS: Final = frozenset({"motion", "occupancy", "presence"})

# Compiled regex patterns with word boundaries to prevent false positives
# e.g., "indoor" won't match "door", but "front_door" will
# Uses lookbehind/lookahead that excludes letters but allows underscores/dots
SAFETY_REGEX: Pattern[str] = re.compile(
    r"(?<![a-zA-Z])(smoke|co2|carbon|leak|flood|water_sensor|gas)(?![a-zA-Z])",
    re.IGNORECASE,
)
SECURITY_REGEX: Pattern[str] = re.compile(
    r"(?<![a-zA-Z])(door|window|lock|alarm|siren|garage)(?![a-zA-Z])",
    re.IGNORECASE,
)
DEVICE_REGEX: Pattern[str] = re.compile(
    r"(?<![a-zA-Z])(battery|offline|unavailable|connectivity)(?![a-zA-Z])",
    re.IGNORECASE,
)
MOTION_REGEX: Pattern[str] = re.compile(
    r"(?<![a-zA-Z])(motion|occupancy|presence)(?![a-zA-Z])",
    re.IGNORECASE,
)

# Device class to category mapping (binary_sensor device classes)
DEVICE_CLASS_CATEGORY_MAP: dict[str, Category] = {
    # Safety - highest priority
    "smoke": Category.SAFETY,
    "carbon_monoxide": Category.SAFETY,
    "gas": Category.SAFETY,
    "moisture": Category.SAFETY,
    "heat": Category.SAFETY,
    "safety": Category.SAFETY,
    # Security
    "door": Category.SECURITY,
    "window": Category.SECURITY,
    "lock": Category.SECURITY,
    "garage_door": Category.SECURITY,
    "opening": Category.SECURITY,
    "tamper": Category.SECURITY,
    # Device health
    "battery": Category.DEVICE,
    "battery_charging": Category.DEVICE,
    "connectivity": Category.DEVICE,
    "problem": Category.DEVICE,
    "plug": Category.DEVICE,
    "power": Category.DEVICE,
    "update": Category.DEVICE,
    # Motion
    "motion": Category.MOTION,
    "occupancy": Category.MOTION,
    "presence": Category.MOTION,
    "moving": Category.MOTION,
}

# Entity domain to category mapping (fallback for entities without device_class)
DOMAIN_CATEGORY_MAP: dict[str, Category] = {
    "alarm_control_panel": Category.SECURITY,
    "lock": Category.SECURITY,
    "siren": Category.SECURITY,
}

# Service
SERVICE_NOTIFY: Final = "notify"
ATTR_MESSAGE: Final = "message"
ATTR_TITLE: Final = "title"
ATTR_DATA: Final = "data"
ATTR_CATEGORY: Final = "category"
ATTR_ENTITY_ID: Final = "entity_id"
ATTR_PRIORITY: Final = "priority"
