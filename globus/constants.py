import functools
from pathlib import Path

import click

# GLOBUS
CLIENT_ID = "fbb557b2-aa0b-42e9-9a07-04c5c4f01474"

# UPDATE
GIT_REPO_URL = "https://github.com/JoshKarpel/globus-transfer"

# SETTINGS
SETTINGS_FILE_DEFAULT_PATH = Path.home() / ".globus_transfer_settings"
AUTH = "auth"
BOOKMARKS = "bookmarks"
REFRESH_TOKEN = "refresh_token"

# CLI
AS_JOB = "--as-submit-description"
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# ERROR CODES
AUTHORIZATION_ERROR = 1
ENDPOINT_ACTIVATION_ERROR = 1
ENDPOINT_INFO_ERROR = 1
INVALID_TRANSFER_SPECIFICATION_ERROR = 1
CANCEL_TASK_ERROR = 1
WAIT_TASK_ERROR = 1
WAIT_TASK_TIMEOUT = 5
UPGRADE_ERROR = 1
NEEDS_USER_INPUT = 2

# FORMATTING
BOLD_HEADER = functools.partial(click.style, bold=True)
BOOKMARKS_LS_COLUMN_ALIGNMENTS = {"endpoint": "ljust", "bookmark": "ljust"}
DEFAULT_ENDPOINTS_HEADERS = ["id", "display_name"]
ENDPOINTS_COLUMN_ALIGNMENTS = {"id": "ljust", "display_name": "ljust"}
DEFAULT_HISTORY_HEADERS = [
    "task_id",
    "label",
    "status",
    "source_endpoint",
    "destination_endpoint",
    "completion_time",
]
HISTORY_COLUMN_ALIGNMENTS = {"task_id": "ljust", "label": "ljust"}
DEFAULT_LS_HEADERS = ["DATA_TYPE", "name", "size"]
LS_COLUMN_ALIGNMENTS = {"DATA_TYPE": "ljust", "name": "ljust"}
ENDPOINT_ACTIVATION_REQUIRED = "GlobusEndpointActivationRequired"
JOB_STATUS_TO_COLOR = {"IDLE": "yellow", "RUNNING": "green", "HELD": "red"}

# HTCONDOR
VANILLA_UNIVERSE = 5
LOCAL_UNIVERSE = 12
UNIVERSE = {5: "VANILLA", 12: "LOCAL"}
JOB_STATUS = {1: "IDLE", 2: "RUNNING", 3: "REMOVED", 4: "COMPLETED", 5: "HELD"}
