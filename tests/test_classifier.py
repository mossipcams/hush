"""Tests for the Hush classifier."""

from unittest.mock import MagicMock

import pytest

from custom_components.hush.classifier import (
    EntityClassifier,
    classify_entity,
    classify_entity_with_confidence,
)
from custom_components.hush.const import CONF_ENTITY_OVERRIDES, Category


class TestClassifyEntity:
    """Tests for classify_entity function."""

    @pytest.mark.parametrize(
        ("entity_id", "expected"),
        [
            # Safety entities
            ("binary_sensor.smoke_detector", Category.SAFETY),
            ("binary_sensor.kitchen_smoke", Category.SAFETY),
            ("sensor.co2_level", Category.SAFETY),
            ("binary_sensor.carbon_monoxide", Category.SAFETY),
            ("binary_sensor.water_leak", Category.SAFETY),
            ("binary_sensor.basement_flood", Category.SAFETY),
            ("binary_sensor.water_sensor_kitchen", Category.SAFETY),
            ("binary_sensor.gas_detector", Category.SAFETY),
            # Security entities
            ("binary_sensor.front_door", Category.SECURITY),
            ("binary_sensor.back_door_contact", Category.SECURITY),
            ("binary_sensor.living_room_window", Category.SECURITY),
            ("lock.front_door", Category.SECURITY),
            ("alarm_control_panel.home", Category.SECURITY),
            ("switch.siren", Category.SECURITY),
            ("cover.garage_door", Category.SECURITY),
            # Device entities
            ("sensor.phone_battery", Category.DEVICE),
            ("sensor.temperature_sensor_battery_level", Category.DEVICE),
            ("binary_sensor.router_offline", Category.DEVICE),
            ("sensor.hub_connectivity", Category.DEVICE),
            # Motion entities
            ("binary_sensor.hallway_motion", Category.MOTION),
            ("binary_sensor.living_room_occupancy", Category.MOTION),
            ("binary_sensor.bedroom_presence", Category.MOTION),
            # Info (default) entities
            ("sensor.temperature", Category.INFO),
            ("light.living_room", Category.INFO),
            ("switch.coffee_maker", Category.INFO),
            ("sensor.energy_usage", Category.INFO),
        ],
    )
    def test_classify_entity(self, entity_id: str, expected: Category) -> None:
        """Test entity classification."""
        assert classify_entity(entity_id) == expected

    def test_classify_empty_entity(self) -> None:
        """Test classification of empty entity ID."""
        assert classify_entity("") == Category.INFO
        assert classify_entity(None) == Category.INFO  # type: ignore[arg-type]

    def test_classify_case_insensitive(self) -> None:
        """Test that classification is case-insensitive."""
        assert classify_entity("binary_sensor.SMOKE_DETECTOR") == Category.SAFETY
        assert classify_entity("binary_sensor.Front_Door") == Category.SECURITY

    def test_safety_priority(self) -> None:
        """Test that safety takes priority over other categories."""
        # An entity with both smoke and door in the name should be SAFETY
        assert classify_entity("binary_sensor.smoke_detector_door") == Category.SAFETY


class TestClassifyEntityWithConfidence:
    """Tests for classify_entity_with_confidence function."""

    def test_returns_category_and_confidence(self) -> None:
        """Test that function returns both category and confidence."""
        category, confidence = classify_entity_with_confidence("binary_sensor.smoke_detector")
        assert category == Category.SAFETY
        assert 0.0 <= confidence <= 1.0

    def test_empty_entity_zero_confidence(self) -> None:
        """Test that empty entity has zero confidence."""
        category, confidence = classify_entity_with_confidence("")
        assert category == Category.INFO
        assert confidence == 0.0

    def test_no_match_zero_confidence(self) -> None:
        """Test that unmatched entity has zero confidence."""
        category, confidence = classify_entity_with_confidence("light.living_room")
        assert category == Category.INFO
        assert confidence == 0.0

    def test_longer_pattern_higher_confidence(self) -> None:
        """Test that longer pattern matches have higher confidence."""
        # water_sensor is longer than leak, should have higher confidence
        _, conf_short = classify_entity_with_confidence("binary_sensor.leak")
        _, conf_long = classify_entity_with_confidence("binary_sensor.water_sensor")
        assert conf_long >= conf_short


class TestWordBoundaryPatterns:
    """Tests for word boundary pattern matching."""

    def test_indoor_does_not_match_door(self) -> None:
        """Test that 'indoor' does not match 'door' pattern."""
        assert classify_entity("sensor.indoor_temperature") == Category.INFO
        assert classify_entity("binary_sensor.indoor_humidity") == Category.INFO

    def test_door_with_underscore_matches(self) -> None:
        """Test that 'front_door' still matches 'door' pattern."""
        assert classify_entity("binary_sensor.front_door") == Category.SECURITY
        assert classify_entity("binary_sensor.back_door_contact") == Category.SECURITY
        assert classify_entity("cover.garage_door") == Category.SECURITY

    def test_word_boundary_at_start(self) -> None:
        """Test word boundary matching at start of entity name."""
        assert classify_entity("binary_sensor.door_sensor") == Category.SECURITY
        assert classify_entity("binary_sensor.motion_living_room") == Category.MOTION

    def test_word_boundary_at_end(self) -> None:
        """Test word boundary matching at end of entity name."""
        assert classify_entity("binary_sensor.living_room_motion") == Category.MOTION
        assert classify_entity("binary_sensor.main_door") == Category.SECURITY

    def test_commodity_does_not_match_motion(self) -> None:
        """Test that words containing 'motion' as substring don't match."""
        # 'commotion' contains 'motion' but shouldn't match with word boundaries
        assert classify_entity("sensor.commotion_level") == Category.INFO

    def test_pattern_matching_with_dots(self) -> None:
        """Test pattern matching with domain.entity format."""
        assert classify_entity("lock.front_door") == Category.SECURITY
        assert classify_entity("alarm_control_panel.smoke_alarm") == Category.SAFETY


class TestEntityClassifier:
    """Tests for EntityClassifier class."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create a mock Home Assistant instance."""
        return MagicMock()

    @pytest.fixture
    def mock_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.options = {}
        return entry

    @pytest.fixture
    def classifier(self, mock_hass: MagicMock, mock_entry: MagicMock) -> EntityClassifier:
        """Create an EntityClassifier instance."""
        return EntityClassifier(mock_hass, mock_entry)

    def test_user_override_takes_priority(
        self, mock_hass: MagicMock, mock_entry: MagicMock
    ) -> None:
        """Test that user overrides have highest priority."""
        mock_entry.options = {
            CONF_ENTITY_OVERRIDES: {
                "binary_sensor.smoke_detector": "info",  # Override safety to info
            }
        }
        classifier = EntityClassifier(mock_hass, mock_entry)

        # Set up mock entity registry
        mock_reg = MagicMock()
        mock_reg.async_get.return_value = None
        classifier._entity_registry = mock_reg

        result = classifier.classify("binary_sensor.smoke_detector")

        # Should be INFO because of override, not SAFETY
        assert result == Category.INFO

    def test_device_class_classification(self, classifier: EntityClassifier) -> None:
        """Test classification by device_class."""
        mock_entity = MagicMock()
        mock_entity.device_class = "smoke"
        mock_entity.original_device_class = None

        mock_reg = MagicMock()
        mock_reg.async_get.return_value = mock_entity
        classifier._entity_registry = mock_reg

        result = classifier.classify("binary_sensor.test_sensor")

        assert result == Category.SAFETY

    def test_device_class_priority_over_pattern(self, classifier: EntityClassifier) -> None:
        """Test that device_class takes priority over pattern matching."""
        # Entity with "door" in name but device_class is "motion"
        mock_entity = MagicMock()
        mock_entity.device_class = "motion"
        mock_entity.original_device_class = None

        mock_reg = MagicMock()
        mock_reg.async_get.return_value = mock_entity
        classifier._entity_registry = mock_reg

        result = classifier.classify("binary_sensor.door_motion")

        # Should be MOTION (from device_class), not SECURITY (from pattern)
        assert result == Category.MOTION

    def test_original_device_class_used_as_fallback(self, classifier: EntityClassifier) -> None:
        """Test that original_device_class is used if device_class is None."""
        mock_entity = MagicMock()
        mock_entity.device_class = None
        mock_entity.original_device_class = "door"

        mock_reg = MagicMock()
        mock_reg.async_get.return_value = mock_entity
        classifier._entity_registry = mock_reg

        result = classifier.classify("binary_sensor.test")

        assert result == Category.SECURITY

    def test_domain_classification(self, classifier: EntityClassifier) -> None:
        """Test classification by domain."""
        mock_reg = MagicMock()
        mock_reg.async_get.return_value = None
        classifier._entity_registry = mock_reg

        result = classifier.classify("lock.front_door")

        # lock domain should map to SECURITY
        assert result == Category.SECURITY

    def test_falls_back_to_pattern(self, classifier: EntityClassifier) -> None:
        """Test fallback to pattern matching when no other match."""
        mock_reg = MagicMock()
        mock_reg.async_get.return_value = None
        classifier._entity_registry = mock_reg

        result = classifier.classify("binary_sensor.smoke_detector")

        assert result == Category.SAFETY

    def test_classify_with_source_override(
        self, mock_hass: MagicMock, mock_entry: MagicMock
    ) -> None:
        """Test classify_with_source returns 'override' for user overrides."""
        mock_entry.options = {CONF_ENTITY_OVERRIDES: {"binary_sensor.test": "security"}}
        classifier = EntityClassifier(mock_hass, mock_entry)

        category, source = classifier.classify_with_source("binary_sensor.test")

        assert category == Category.SECURITY
        assert source == "override"

    def test_classify_with_source_device_class(self, classifier: EntityClassifier) -> None:
        """Test classify_with_source returns 'device_class' source."""
        mock_entity = MagicMock()
        mock_entity.device_class = "motion"
        mock_entity.original_device_class = None

        mock_reg = MagicMock()
        mock_reg.async_get.return_value = mock_entity
        classifier._entity_registry = mock_reg

        category, source = classifier.classify_with_source("binary_sensor.test")

        assert category == Category.MOTION
        assert source == "device_class"

    def test_classify_with_source_domain(self, classifier: EntityClassifier) -> None:
        """Test classify_with_source returns 'domain' source."""
        mock_reg = MagicMock()
        mock_reg.async_get.return_value = None
        classifier._entity_registry = mock_reg

        category, source = classifier.classify_with_source("lock.test")

        assert category == Category.SECURITY
        assert source == "domain"

    def test_classify_with_source_pattern(self, classifier: EntityClassifier) -> None:
        """Test classify_with_source returns 'pattern' source."""
        mock_reg = MagicMock()
        mock_reg.async_get.return_value = None
        classifier._entity_registry = mock_reg

        category, source = classifier.classify_with_source("binary_sensor.smoke_detector")

        assert category == Category.SAFETY
        assert source == "pattern"

    def test_classify_with_source_default(self, classifier: EntityClassifier) -> None:
        """Test classify_with_source returns 'default' for unmatched entities."""
        mock_reg = MagicMock()
        mock_reg.async_get.return_value = None
        classifier._entity_registry = mock_reg

        category, source = classifier.classify_with_source("light.living_room")

        assert category == Category.INFO
        assert source == "default"

    def test_classify_empty_entity(self, classifier: EntityClassifier) -> None:
        """Test classification of empty entity ID."""
        assert classifier.classify("") == Category.INFO

    def test_classify_with_source_empty_entity(self, classifier: EntityClassifier) -> None:
        """Test classify_with_source with empty entity ID."""
        category, source = classifier.classify_with_source("")
        assert category == Category.INFO
        assert source == "default"
