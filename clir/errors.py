"""Exception hierarchy for clir.

ClirError is the base for any framework-raised error. User commands may also
raise ClirError (or its subclasses) to surface a styled message and a
specific exit code without leaking a traceback.
"""

from __future__ import annotations


class ClirError(Exception):
    """Base class for framework-raised errors.

    Carries a human-readable message and an exit_code. The dispatcher prints
    the message via the styled error() function and exits with the given
    code, never showing a traceback unless --debug is set.
    """

    exit_code: int = 1

    def __init__(self, message: str, *, exit_code: int | None = None):
        super().__init__(message)
        self.message = message
        if exit_code is not None:
            self.exit_code = exit_code


class UsageError(ClirError):
    """Bad CLI input from the user (unknown command, missing arg, bad value).

    Conventionally exits with code 2 to distinguish from a runtime error.
    """

    exit_code = 2
