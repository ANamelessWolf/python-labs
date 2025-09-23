import inspect
import sys
from datetime import datetime


def _timestamp() -> str:
    """Returns the current timestamp in a human-readable format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_api_call(topic: str, details: str = "") -> None:
    """
    Logs a Spotify API call to the console with a timestamp and topic.

    Args:
        topic (str): A short description of the API call.
        details (str): Optional extra details about the request.
    """
    ts = _timestamp()
    msg = f"[{ts}] [API CALL] {topic}"
    if details:
        msg += f" | {details}"
    print(msg)


def log_error(exception: Exception) -> None:
    """
    Logs an error with timestamp, function name, and the exception message.

    Args:
        exception (Exception): The caught exception to log.
    """
    ts = _timestamp()
    func_name = inspect.stack()[1].function  # function that called log_error
    exc_type = type(exception).__name__
    msg = f"[{ts}] [ERROR] in {func_name} -> {exc_type}: {exception}"
    print(msg, file=sys.stderr)
