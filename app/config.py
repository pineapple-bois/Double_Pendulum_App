import os


TRUTHY_VALUES = {"1", "true", "yes", "on"}


def env_bool(name: str, default: bool = False) -> bool:
    """Return a boolean environment flag using common truthy values."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in TRUTHY_VALUES


FORCE_HTTPS = env_bool("FORCE_HTTPS", default=False)
DASH_DEBUG = env_bool("DASH_DEBUG", default=False)
