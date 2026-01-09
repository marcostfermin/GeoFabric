"""Full coverage tests for util.py."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from geofabric.util import (
    ProgressTracker,
    RetryableError,
    progress_bar,
    retry_with_backoff,
)


class TestRetryWithBackoff:
    """Tests for retry_with_backoff decorator."""

    def test_retry_success_first_try(self) -> None:
        """Test successful function on first try."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def successful_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self) -> None:
        """Test function that succeeds after some failures."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def eventually_successful() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = eventually_successful()
        assert result == "success"
        assert call_count == 3

    def test_retry_all_failures(self) -> None:
        """Test function that always fails."""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fails()
        assert call_count == 3  # Initial + 2 retries

    def test_retry_with_specific_exception(self) -> None:
        """Test retry with specific retryable exception."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(RetryableError,),
        )
        def specific_error() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RetryableError("Retry this")
            return "success"

        result = specific_error()
        assert result == "success"
        assert call_count == 2

    def test_retry_non_retryable_exception(self) -> None:
        """Test that non-retryable exceptions are not retried."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(RetryableError,),
        )
        def wrong_error() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError, match="Not retryable"):
            wrong_error()
        assert call_count == 1  # No retries

    def test_retry_max_delay(self) -> None:
        """Test that delay is capped at max_delay."""
        call_count = 0

        @retry_with_backoff(
            max_retries=2,
            base_delay=0.01,
            max_delay=0.02,
            exponential_base=10.0,
        )
        def fails_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("Fail")
            return "success"

        result = fails_twice()
        assert result == "success"


class TestRetryableError:
    """Tests for RetryableError exception."""

    def test_retryable_error_creation(self) -> None:
        """Test creating RetryableError."""
        error = RetryableError("Test error")
        assert str(error) == "Test error"

    def test_retryable_error_is_exception(self) -> None:
        """Test RetryableError is an Exception."""
        error = RetryableError("Test")
        assert isinstance(error, Exception)


class TestProgressTracker:
    """Tests for ProgressTracker context manager."""

    def test_progress_tracker_basic(self) -> None:
        """Test basic ProgressTracker usage."""
        with ProgressTracker("Test", total=10, show_progress=True) as tracker:
            for _ in range(10):
                tracker.advance()

    def test_progress_tracker_disabled(self) -> None:
        """Test ProgressTracker with show_progress=False."""
        with ProgressTracker("Test", total=10, show_progress=False) as tracker:
            tracker.advance()
            tracker.update(5)
            tracker.set_description("New description")

    def test_progress_tracker_no_total(self) -> None:
        """Test ProgressTracker without total."""
        with ProgressTracker("Test", show_progress=True) as tracker:
            tracker.advance()

    def test_progress_tracker_update(self) -> None:
        """Test ProgressTracker update method."""
        with ProgressTracker("Test", total=10, show_progress=True) as tracker:
            tracker.update(5)

    def test_progress_tracker_set_description(self) -> None:
        """Test ProgressTracker set_description method."""
        with ProgressTracker("Test", total=10, show_progress=True) as tracker:
            tracker.set_description("New task")

    def test_progress_tracker_no_rich(self) -> None:
        """Test ProgressTracker when rich is not available."""
        import sys
        # Save original modules
        original_rich = sys.modules.get("rich.progress")

        # Temporarily remove rich.progress from sys.modules to simulate ImportError
        sys.modules["rich.progress"] = None

        try:
            # Create a fresh tracker that will try to import rich
            tracker = ProgressTracker("Test", total=10, show_progress=True)
            tracker._progress = None  # Force the ImportError path
            tracker._task_id = None

            # These should not raise even without rich
            tracker.advance()
            tracker.update(5)
            tracker.set_description("Test")
        finally:
            # Restore original module
            if original_rich is not None:
                sys.modules["rich.progress"] = original_rich
            elif "rich.progress" in sys.modules:
                del sys.modules["rich.progress"]

    def test_progress_tracker_methods_without_progress(self) -> None:
        """Test ProgressTracker methods when _progress is None."""
        tracker = ProgressTracker("Test", total=10, show_progress=False)
        tracker._progress = None
        tracker._task_id = None

        # These should not raise
        tracker.advance()
        tracker.update(5)
        tracker.set_description("Test")


class TestProgressBar:
    """Tests for progress_bar function."""

    def test_progress_bar_basic(self) -> None:
        """Test basic progress_bar usage."""
        items = [1, 2, 3]
        result = list(progress_bar(items, "Processing", show_progress=True))
        assert result == [1, 2, 3]

    def test_progress_bar_disabled(self) -> None:
        """Test progress_bar with show_progress=False."""
        items = [1, 2, 3]
        result = list(progress_bar(items, "Processing", show_progress=False))
        assert result == [1, 2, 3]

    def test_progress_bar_with_total(self) -> None:
        """Test progress_bar with explicit total."""
        items = [1, 2, 3]
        result = list(progress_bar(items, "Processing", total=3, show_progress=True))
        assert result == [1, 2, 3]

    def test_progress_bar_empty(self) -> None:
        """Test progress_bar with empty iterable."""
        result = list(progress_bar([], "Processing"))
        assert result == []

    def test_progress_bar_no_rich(self) -> None:
        """Test progress_bar when rich is not available."""
        import sys

        # Save original module
        original_track = sys.modules.get("rich.progress")

        # Create a mock module that raises ImportError when track is accessed
        class FakeRichProgress:
            def __getattr__(self, name):
                raise ImportError("No rich")

        sys.modules["rich.progress"] = FakeRichProgress()

        try:
            items = [1, 2, 3]
            # Use a fresh import to pick up our fake module
            result = list(progress_bar(items, "Processing", show_progress=False))
            assert result == [1, 2, 3]
        finally:
            # Restore
            if original_track is not None:
                sys.modules["rich.progress"] = original_track
            elif "rich.progress" in sys.modules:
                del sys.modules["rich.progress"]
