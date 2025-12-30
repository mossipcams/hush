"""Entity classification for Hush notifications."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import (
    CONF_ENTITY_OVERRIDES,
    DEVICE_CLASS_CATEGORY_MAP,
    DEVICE_REGEX,
    DOMAIN_CATEGORY_MAP,
    MOTION_REGEX,
    SAFETY_REGEX,
    SECURITY_REGEX,
    Category,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_registry import EntityRegistry


class EntityClassifier:
    """Classify entities into notification categories.

    Uses a priority-based classification system:
    1. User overrides (from config entry options) - highest priority
    2. device_class from Home Assistant entity registry
    3. Entity domain (e.g., lock, alarm_control_panel)
    4. Pattern matching on entity_id (with word boundaries)
    5. Default to INFO category
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the classifier.

        Args:
            hass: Home Assistant instance for entity registry access
            entry: Config entry for user overrides
        """
        self._hass = hass
        self._entry = entry
        self._entity_registry: EntityRegistry | None = None

    @property
    def entity_registry(self) -> EntityRegistry:
        """Lazily get the entity registry."""
        if self._entity_registry is None:
            from homeassistant.helpers import entity_registry as er

            self._entity_registry = er.async_get(self._hass)
        return self._entity_registry

    def classify(self, entity_id: str) -> Category:
        """Classify an entity into a notification category.

        Priority order:
        1. User overrides (from config entry options)
        2. device_class from entity registry
        3. Domain-based classification
        4. Pattern matching (with word boundaries)
        5. Default (INFO)

        Args:
            entity_id: The entity ID to classify

        Returns:
            The category for this entity
        """
        if not entity_id:
            return Category.INFO

        # 1. Check user overrides first (highest priority)
        overrides = self._entry.options.get(CONF_ENTITY_OVERRIDES, {})
        if entity_id in overrides:
            return Category(overrides[entity_id])

        # 2. Check device_class from entity registry
        category = self._classify_by_device_class(entity_id)
        if category:
            return category

        # 3. Check domain-based classification
        category = self._classify_by_domain(entity_id)
        if category:
            return category

        # 4. Fall back to pattern matching
        return self._classify_by_pattern(entity_id)

    def _classify_by_device_class(self, entity_id: str) -> Category | None:
        """Classify based on entity registry device_class."""
        entry = self.entity_registry.async_get(entity_id)
        if not entry:
            return None

        # Use device_class (can be overridden) or original_device_class (from device)
        device_class = entry.device_class or entry.original_device_class
        if device_class and device_class in DEVICE_CLASS_CATEGORY_MAP:
            return DEVICE_CLASS_CATEGORY_MAP[device_class]

        return None

    def _classify_by_domain(self, entity_id: str) -> Category | None:
        """Classify based on entity domain."""
        domain = entity_id.split(".")[0] if "." in entity_id else None
        if domain and domain in DOMAIN_CATEGORY_MAP:
            return DOMAIN_CATEGORY_MAP[domain]
        return None

    def _classify_by_pattern(self, entity_id: str) -> Category:
        """Classify using regex patterns with word boundaries.

        Priority: Safety > Security > Device > Motion > Info
        """
        # Safety patterns - highest priority
        if SAFETY_REGEX.search(entity_id):
            return Category.SAFETY

        # Security patterns
        if SECURITY_REGEX.search(entity_id):
            return Category.SECURITY

        # Device health patterns
        if DEVICE_REGEX.search(entity_id):
            return Category.DEVICE

        # Motion patterns
        if MOTION_REGEX.search(entity_id):
            return Category.MOTION

        # Default fallback
        return Category.INFO

    def classify_with_source(self, entity_id: str) -> tuple[Category, str]:
        """Classify entity and return the classification source.

        Useful for debugging and UI display.

        Returns:
            Tuple of (Category, source) where source is one of:
            "override", "device_class", "domain", "pattern", "default"
        """
        if not entity_id:
            return Category.INFO, "default"

        # 1. User overrides
        overrides = self._entry.options.get(CONF_ENTITY_OVERRIDES, {})
        if entity_id in overrides:
            return Category(overrides[entity_id]), "override"

        # 2. Device class
        category = self._classify_by_device_class(entity_id)
        if category:
            return category, "device_class"

        # 3. Domain
        category = self._classify_by_domain(entity_id)
        if category:
            return category, "domain"

        # 4. Pattern matching
        for pattern, cat in [
            (SAFETY_REGEX, Category.SAFETY),
            (SECURITY_REGEX, Category.SECURITY),
            (DEVICE_REGEX, Category.DEVICE),
            (MOTION_REGEX, Category.MOTION),
        ]:
            if pattern.search(entity_id):
                return cat, "pattern"

        return Category.INFO, "default"


def classify_entity(entity_id: str) -> Category:
    """Infer notification category from entity_id patterns.

    This is a legacy function for backwards compatibility.
    For full classification with device_class and overrides,
    use EntityClassifier.classify().

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

    # Safety - highest priority
    if SAFETY_REGEX.search(entity_id):
        return Category.SAFETY

    # Security
    if SECURITY_REGEX.search(entity_id):
        return Category.SECURITY

    # Device health
    if DEVICE_REGEX.search(entity_id):
        return Category.DEVICE

    # Motion
    if MOTION_REGEX.search(entity_id):
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

    # Check patterns and collect matches
    matches: list[tuple[Category, str]] = []

    for pattern, cat in [
        (SAFETY_REGEX, Category.SAFETY),
        (SECURITY_REGEX, Category.SECURITY),
        (DEVICE_REGEX, Category.DEVICE),
        (MOTION_REGEX, Category.MOTION),
    ]:
        match = pattern.search(entity_id)
        if match:
            matches.append((cat, match.group()))

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
