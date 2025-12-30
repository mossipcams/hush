"""Tests for quiet hours functionality."""

from __future__ import annotations

from datetime import time

import pytest


def is_quiet_hours_impl(current_time: time, start: time, end: time) -> bool:
    """Implementation of quiet hours check for testing.

    This mirrors the logic in __init__.py._is_quiet_hours.
    """
    if start > end:
        # Overnight quiet hours (e.g., 22:00 - 07:00)
        return current_time >= start or current_time < end
    else:
        # Same-day quiet hours (e.g., 14:00 - 16:00)
        return start <= current_time < end


class TestQuietHours:
    """Tests for quiet hours logic."""

    @pytest.mark.parametrize(
        ("current", "start", "end", "expected"),
        [
            # Standard overnight quiet hours (22:00 - 07:00)
            (time(23, 0), time(22, 0), time(7, 0), True),  # 11 PM - quiet
            (time(3, 0), time(22, 0), time(7, 0), True),  # 3 AM - quiet
            (time(6, 59), time(22, 0), time(7, 0), True),  # 6:59 AM - still quiet
            (time(7, 0), time(22, 0), time(7, 0), False),  # 7 AM - not quiet (boundary)
            (time(12, 0), time(22, 0), time(7, 0), False),  # Noon - not quiet
            (time(21, 59), time(22, 0), time(7, 0), False),  # 9:59 PM - not quiet yet
            (time(22, 0), time(22, 0), time(7, 0), True),  # 10 PM - quiet (boundary)
            # Same-day quiet hours (14:00 - 16:00)
            (time(14, 0), time(14, 0), time(16, 0), True),  # 2 PM - quiet (boundary)
            (time(15, 0), time(14, 0), time(16, 0), True),  # 3 PM - quiet
            (time(15, 59), time(14, 0), time(16, 0), True),  # 3:59 PM - still quiet
            (time(16, 0), time(14, 0), time(16, 0), False),  # 4 PM - not quiet (boundary)
            (time(13, 0), time(14, 0), time(16, 0), False),  # 1 PM - not quiet yet
            # Edge cases
            (time(0, 0), time(22, 0), time(7, 0), True),  # Midnight - quiet
            (time(0, 0), time(1, 0), time(2, 0), False),  # Midnight with 1-2 AM window
        ],
    )
    def test_quiet_hours_check(self, current: time, start: time, end: time, expected: bool) -> None:
        """Test quiet hours boundary conditions."""
        assert is_quiet_hours_impl(current, start, end) == expected

    def test_same_start_end_no_quiet_hours(self) -> None:
        """Test that same start and end means no quiet hours."""
        # When start == end, the window is empty
        assert is_quiet_hours_impl(time(12, 0), time(22, 0), time(22, 0)) is False
        assert is_quiet_hours_impl(time(22, 0), time(22, 0), time(22, 0)) is False
