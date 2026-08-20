import os


TRUTHY_VALUES = {"1", "true", "yes", "on"}
PRODUCTION_TRUSTED_HOSTS = (
    "double-pendulum.net",
    "www.double-pendulum.net",
    "web-production-65a59.up.railway.app",
)


def env_bool(name: str, default: bool = False) -> bool:
    """Return a boolean environment flag using common truthy values."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in TRUTHY_VALUES


FORCE_HTTPS = env_bool("FORCE_HTTPS", default=False)
DASH_DEBUG = env_bool("DASH_DEBUG", default=False)
# FORCE_HTTPS is the verified production deployment boundary. Local development
# leaves it false, so host validation does not interfere with localhost.
TRUSTED_HOSTS = PRODUCTION_TRUSTED_HOSTS if FORCE_HTTPS else None
