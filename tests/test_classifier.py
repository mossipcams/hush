"""Tests for the Hush classifier."""

import pytest

from custom_components.hush.classifier import classify_entity, classify_entity_with_confidence
from custom_components.hush.const import Category


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
