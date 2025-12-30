"""Entity classification for Hush notifications."""

from __future__ import annotations

from .const import (
    DEVICE_PATTERNS,
    MOTION_PATTERNS,
    SAFETY_PATTERNS,
    SECURITY_PATTERNS,
    Category,
)


def classify_entity(entity_id: str) -> Category:
    """Infer notification category from entity_id patterns.

    Classification priority:
    1. Safety (smoke, CO, leak, flood) - highest priority
    2. Security (doors, windows, locks, alarms)
    3. Device health (battery, connectivity)
    4. Motion (motion, occupancy, presence)
    5. Info (default fallback)

    Args:
        entity_id: The entity ID to classify (e.g., "binary_sensor.front_door")

    Returns:
        The inferred Category for this entity.
    """
    if not entity_id:
        return Category.INFO

    # Normalize for matching
    entity_lower = entity_id.lower()

    # Safety - highest priority (always notify)
    for pattern in SAFETY_PATTERNS:
        if pattern in entity_lower:
            return Category.SAFETY

    # Security
    for pattern in SECURITY_PATTERNS:
        if pattern in entity_lower:
            return Category.SECURITY

    # Device health
    for pattern in DEVICE_PATTERNS:
        if pattern in entity_lower:
            return Category.DEVICE

    # Motion (log only by default)
    for pattern in MOTION_PATTERNS:
        if pattern in entity_lower:
            return Category.MOTION

    # Default
    return Category.INFO


def classify_entity_with_confidence(entity_id: str) -> tuple[Category, float]:
    """Classify entity with a confidence score.

    Useful for UI display or debugging.

    Args:
        entity_id: The entity ID to classify.

    Returns:
        Tuple of (Category, confidence) where confidence is 0.0-1.0.
    """
    if not entity_id:
        return Category.INFO, 0.0

    entity_lower = entity_id.lower()
    matches: list[tuple[Category, str]] = []

    # Check all patterns
    for pattern in SAFETY_PATTERNS:
        if pattern in entity_lower:
            matches.append((Category.SAFETY, pattern))

    for pattern in SECURITY_PATTERNS:
        if pattern in entity_lower:
            matches.append((Category.SECURITY, pattern))

    for pattern in DEVICE_PATTERNS:
        if pattern in entity_lower:
            matches.append((Category.DEVICE, pattern))

    for pattern in MOTION_PATTERNS:
        if pattern in entity_lower:
            matches.append((Category.MOTION, pattern))

    if not matches:
        return Category.INFO, 0.0

    # Priority order determines the result
    priority = [Category.SAFETY, Category.SECURITY, Category.DEVICE, Category.MOTION]

    for cat in priority:
        cat_matches = [m for m in matches if m[0] == cat]
        if cat_matches:
            # Confidence based on pattern specificity (longer = more specific)
            max_len = max(len(m[1]) for m in cat_matches)
            confidence = min(0.5 + (max_len / 20), 1.0)
            return cat, confidence

    return Category.INFO, 0.0
