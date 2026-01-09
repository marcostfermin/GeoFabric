from __future__ import annotations

import os
import shlex
import subprocess  # nosec B404 - required for external tool execution
import time
from collections.abc import Callable, Sequence
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

from geofabric.errors import ExternalToolError

__all__ = [
    "ProgressTracker",
    "RetryableError",
    "ensure_dir",
    "progress_bar",
    "resolve_path",
    "retry_with_backoff",
    "run_cmd",
]

T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (must be >= 0)
        base_delay: Initial delay between retries in seconds (must be > 0)
        max_delay: Maximum delay between retries in seconds (must be > 0)
        exponential_base: Base for exponential backoff calculation (must be > 0)
        retryable_exceptions: Tuple of exception types that trigger a retry

    Raises:
        ValueError: If parameters are invalid
    """
    # Validate parameters
    if max_retries < 0:
        raise ValueError(f"max_retries must be >= 0, got {max_retries}")
    if base_delay <= 0:
        raise ValueError(f"base_delay must be > 0, got {base_delay}")
    if max_delay <= 0:
        raise ValueError(f"max_delay must be > 0, got {max_delay}")
    if exponential_base <= 0:
        raise ValueError(f"exponential_base must be > 0, got {exponential_base}")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions:
                    if attempt < max_retries:
                        delay = min(base_delay * (exponential_base**attempt), max_delay)
                        time.sleep(delay)
                    else:
                        raise
            raise AssertionError("unreachable")  # pragma: no cover

        return wrapper

    return decorator


class RetryableError(Exception):
    """Exception that indicates an operation should be retried."""

    pass


def ensure_dir(path: str) -> str:
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def resolve_path(path: str) -> str:
    return str(Path(path).expanduser().resolve())


def run_cmd(
    args: Sequence[str],
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    check: bool = True,
    timeout: float | None = None,
) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr).

    Args:
        args: Command and arguments to run (must not be empty)
        env: Additional environment variables
        cwd: Working directory
        check: If True, raise ExternalToolError on non-zero exit
        timeout: Timeout in seconds (None = no timeout, must be > 0 if specified)

    Raises:
        ValueError: If args is empty or timeout is invalid
        ExternalToolError: If check=True and command fails
    """
    # Validate arguments
    if not args:
        raise ValueError("args must not be empty")
    if timeout is not None and timeout <= 0:
        raise ValueError(f"timeout must be > 0, got {timeout}")

    proc = subprocess.Popen(  # nosec B603
        list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, **(env or {})},
        cwd=cwd,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()  # Clean up
        cmd_str = " ".join(shlex.quote(a) for a in args)
        raise ExternalToolError(f"Command timed out after {timeout}s: {cmd_str}") from None
    if check and proc.returncode != 0:
        cmd_str = " ".join(shlex.quote(a) for a in args)
        # Truncate output to prevent sensitive information disclosure
        # External tools may print credentials, API keys, or other secrets in error output
        max_output_len = 1000
        truncated_out = out[:max_output_len] + "..." if len(out) > max_output_len else out
        truncated_err = err[:max_output_len] + "..." if len(err) > max_output_len else err
        raise ExternalToolError(
            f"Command failed (code={proc.returncode}): {cmd_str}\n\n"
            f"STDOUT (truncated):\n{truncated_out}\n\n"
            f"STDERR (truncated):\n{truncated_err}",
            tool=args[0] if args else None,
            exit_code=proc.returncode,
            stderr=truncated_err,
        )
    return proc.returncode, out, err


class ProgressTracker:
    """Context manager for tracking progress with rich progress bars.

    Example:
        with ProgressTracker("Processing files", total=100) as progress:
            for item in items:
                process(item)
                progress.advance()
    """

    def __init__(
        self,
        description: str = "Processing",
        total: int | None = None,
        show_progress: bool = True,
    ):
        self.description = description
        self.total = total
        self.show_progress = show_progress
        self._progress: Any = None
        self._task_id: Any = None

    def __enter__(self) -> ProgressTracker:
        if self.show_progress:
            try:
                from rich.progress import (
                    BarColumn,
                    Progress,
                    SpinnerColumn,
                    TextColumn,
                    TimeElapsedColumn,
                    TimeRemainingColumn,
                )

                columns = [
                    SpinnerColumn(),
                    TextColumn("[bold blue]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeElapsedColumn(),
                    TimeRemainingColumn(),
                ]
                self._progress = Progress(*columns)
                self._progress.start()
                self._task_id = self._progress.add_task(
                    self.description,
                    total=self.total,
                )
            except ImportError:
                pass  # rich not available
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._progress is not None:
            self._progress.stop()

    def advance(self, amount: int = 1) -> None:
        """Advance the progress bar."""
        if self._progress is not None and self._task_id is not None:
            self._progress.advance(self._task_id, amount)

    def update(self, completed: int) -> None:
        """Set the absolute progress value."""
        if self._progress is not None and self._task_id is not None:
            self._progress.update(self._task_id, completed=completed)

    def set_description(self, description: str) -> None:
        """Update the progress description."""
        if self._progress is not None and self._task_id is not None:
            self._progress.update(self._task_id, description=description)


def progress_bar(
    iterable: Any,
    description: str = "Processing",
    total: int | None = None,
    show_progress: bool = True,
) -> Any:
    """Wrap an iterable with a progress bar.

    Example:
        for item in progress_bar(items, "Processing"):
            process(item)
    """
    if not show_progress:
        yield from iterable
        return

    try:
        from rich.progress import track

        yield from track(iterable, description=description, total=total)
    except ImportError:
        yield from iterable
