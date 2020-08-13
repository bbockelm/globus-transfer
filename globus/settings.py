import logging

import toml

from .constants import AUTH, BOOKMARKS, SETTINGS_FILE_DEFAULT_PATH

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def save_settings(settings, path=None):
    path = path or SETTINGS_FILE_DEFAULT_PATH

    with path.open(mode="w") as f:
        toml.dump(settings, f)

    logger.debug(f"Wrote current settings to {path}")

    return path


def load_settings(path=None):
    path = path or SETTINGS_FILE_DEFAULT_PATH

    try:
        settings = toml.load(path)
        logger.debug(f"Read settings from {path}")
    except FileNotFoundError:
        settings = {}
        logger.debug(f"No settings file found at {path}, using blank settings")

    settings.setdefault(AUTH, {})
    settings.setdefault(BOOKMARKS, {})

    return settings
