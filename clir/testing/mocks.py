"""Testing utilities for CLI applications."""

from contextlib import contextmanager, ExitStack
from io import StringIO
from typing import Any, Generator
import sys


class MockConsole:
    """Mock console for testing output."""

    def __init__(self):
        self.output = StringIO()
        self.errors = StringIO()

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Capture print output."""
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        output = sep.join(str(a) for a in args) + end
        self.output.write(output)

    def print_error(self, *args: Any, **kwargs: Any) -> None:
        """Capture error output."""
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        output = sep.join(str(a) for a in args) + end
        self.errors.write(output)

    def get_output(self) -> str:
        """Get captured stdout."""
        return self.output.getvalue()

    def get_errors(self) -> str:
        """Get captured stderr."""
        return self.errors.getvalue()

    def clear(self) -> None:
        """Clear captured output."""
        self.output = StringIO()
        self.errors = StringIO()


class MockInput:
    """Mock input for testing prompts."""

    def __init__(self, inputs: list[str]):
        self.inputs = iter(inputs)
        self.responses: list[str] = []

    def input(self, prompt: str = "") -> str:
        """Return next mock input."""
        try:
            response = next(self.inputs)
            self.responses.append(response)
            return response
        except StopIteration:
            raise EOFError("No more mock inputs available")

    def __enter__(self) -> "MockInput":
        return self

    def __exit__(self, *args: Any) -> None:
        pass


@contextmanager
def capture_output() -> Generator[tuple[StringIO, StringIO], None, None]:
    """Context manager to capture stdout and stderr."""
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    stdout_capture = StringIO()
    stderr_capture = StringIO()

    sys.stdout = stdout_capture
    sys.stderr = stderr_capture

    try:
        yield stdout_capture, stderr_capture
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr


class CliRunner:
    """Test runner for CLI applications."""

    def __init__(self, app):
        self.app = app

    def invoke(
        self,
        args: list[str] | None = None,
        prompt_responses: list[str] | None = None,
    ) -> "CliResult":
        """Invoke the CLI with given arguments.

        Args:
            args: Command line arguments
            prompt_responses: List of responses for prompt_toolkit prompts
        """
        args = args or []

        with ExitStack() as stack:
            stdout, stderr = stack.enter_context(capture_output())
            if prompt_responses:
                stack.enter_context(mock_prompt(prompt_responses))
            try:
                self.app.run(args)
                return CliResult(
                    exit_code=0,
                    output=stdout.getvalue(),
                    error=stderr.getvalue(),
                )
            except SystemExit as e:
                return CliResult(
                    exit_code=e.code or 0,
                    output=stdout.getvalue(),
                    error=stderr.getvalue(),
                )
            except Exception as e:
                return CliResult(
                    exit_code=1,
                    output=stdout.getvalue(),
                    error=stderr.getvalue(),
                    exception=e,
                )


class CliResult:
    """Result of CLI invocation."""

    def __init__(
        self,
        exit_code: int,
        output: str,
        error: str,
        exception: Exception | None = None,
    ):
        self.exit_code = exit_code
        self.output = output
        self.error = error
        self.exception = exception

    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return self.exit_code == 0

    def __repr__(self) -> str:
        return f"CliResult(exit_code={self.exit_code}, output={self.output!r})"


@contextmanager
def mock_prompt(responses: list[str]):
    """Context manager to mock prompt_toolkit prompts.

    Args:
        responses: List of responses to return for each prompt call
    """
    response_gen = iter(responses)

    def mock_prompt_response(*args: Any, **kwargs: Any) -> str:
        """Mock prompt function that returns next response."""
        try:
            return next(response_gen)
        except StopIteration:
            raise EOFError("No more mock inputs available")

    import prompt_toolkit
    original_prompt = prompt_toolkit.prompt
    prompt_toolkit.prompt = mock_prompt_response
    try:
        yield
    finally:
        prompt_toolkit.prompt = original_prompt
