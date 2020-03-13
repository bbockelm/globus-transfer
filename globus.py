import logging
import sys
from pathlib import Path
from urllib.parse import urlencode
import datetime
import functools
import subprocess
import pprint
import json
import textwrap

import click
from click_didyoumean import DYMGroup

import toml

import globus_sdk

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.NullHandler())

AUTHORIZATION_ERROR = 1
ENDPOINT_ACTIVATION_ERROR = 1
ENDPOINT_INFO_ERROR = 1
INVALID_TRANSFER_SPECIFICATION_ERROR = 1
CANCEL_TASK_ERROR = 1
WAIT_TASK_ERROR = 1
WAIT_TASK_TIMEOUT = 5
UPGRADE_ERROR = 1

CLIENT_ID = "fbb557b2-aa0b-42e9-9a07-04c5c4f01474"

GIT_REPO_URL = "https://github.com/JoshKarpel/globus-transfer"

SETTINGS_FILE_DEFAULT_PATH = Path.home() / ".globus_transfer_settings"
AUTH = "auth"
BOOKMARKS = "bookmarks"
REFRESH_TOKEN = "refresh_token"

BOLD_HEADER = functools.partial(click.style, bold=True)


AS_JOB = "--as-submit-description"


# CLI

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS, cls=DYMGroup)
@click.option(
    "--verbose",
    "-v",
    count=True,
    default=0,
    help="Show log messages as the CLI runs. Pass more times for more verbosity.",
)
@click.option(
    AS_JOB,
    is_flag=True,
    help="Produce an HTCondor submit description that would execute the command as a job, instead of actually performing the command.",
)
@click.pass_context
def cli(context, verbose, as_submit_description):
    """
    Initial setup: run 'globus login' and following the printed instructions.
    """
    setup_logging(verbose)

    context.obj = load_settings()

    logger.debug(f'{sys.argv[0]} called with arguments "{" ".join(sys.argv[1:])}"')

    if as_submit_description:
        exe, *args = sys.argv
        args_string = " ".join((arg for arg in args if arg != AS_JOB))
        desc = f"""
            universe = local

            executable = {exe}
            arguments = {args_string}

            log = globus_job_$(CLUSTER)_$(PROCESS).log
            output = globus_job_$(CLUSTER)_$(PROCESS).out
            error = globus_job_$(CLUSTER)_$(PROCESS).err

            request_cpus = 1
            request_memory = 200MB
            request_disk = 1GB

            on_exit_hold = ExitCode =!= 0
            on_exit_hold_reason = "globus command failed"

            should_transfer_files = NO
            transfer_executable = False

            +IsGlobusTransferJob = True
            
            queue 1
            """
        click.secho(textwrap.dedent(desc).lstrip())
        sys.exit(0)


# SETTINGS COMMANDS


@cli.command()
@click.option(
    "--version",
    default="master",
    help="Which version to install (branch, tag, or sha [default master]).",
)
@click.option(
    "--dry",
    is_flag=True,
    help="Only show what command would be run; do not actually run it.",
)
def upgrade(version, dry):
    """Upgrade this tool by installing a new version from GitHub."""
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--user",
        "--upgrade",
        f"git+{GIT_REPO_URL}.git@{version}",
    ]

    if dry:
        click.secho(" ".join(cmd))
        return

    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    if p.returncode != 0:
        error(
            f"Upgrade failed! Output from command '{' '.join(cmd)}' reproduced below:\n{p.stdout}\n{p.stderr}",
            exit_code=UPGRADE_ERROR,
        )

    click.secho("Upgraded successfully", fg="green")


@cli.command()
@click.option(
    "--shell",
    required=True,
    type=click.Choice(["bash", "zsh", "fish"], case_sensitive=False),
    help="Which shell program to enable autocompletion for.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Append the autocompletion activation command even if it already exists.",
)
@click.option(
    "--destination",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    default=None,
    help="Append the autocompletion activation command to this file instead of the shell default.",
)
def enable_autocomplete(shell, force, destination):
    """
    Enable autocompletion for the shell of your choice.

    This command should only need to be run once for each shell.

    Note that your Python
    environment must be available (i.e., running "globus" must work) by the time
    the autocompletion-enabling command runs in your shell configuration file.
    """
    cmd, dst = {
        "bash": (
            r'eval "$(_GLOBUS_COMPLETE=source_bash globus)"',
            Path.home() / ".bashrc",
        ),
        "zsh": (
            r'eval "$(_GLOBUS_COMPLETE=source_zsh globus)"',
            Path.home() / ".zshrc",
        ),
        "fish": (
            r"eval (env _GLOBUS_COMPLETE=source_fish foo-bar)",
            Path.home() / ".config" / "fish" / "completions" / "globus.fish",
        ),
    }[shell]

    if destination is not None:
        dst = Path(destination)

    if not force and cmd in dst.read_text():
        click.secho(f"Autocompletion already enabled for {shell}", fg="yellow")
        return

    with dst.open(mode="a") as f:
        f.write(f"\n# enable globus-transfer autocompletion\n{cmd}\n")

    click.secho(
        f"Autocompletion enabled for {shell} (startup command added to {dst})",
        fg="green",
    )


@cli.command()
@click.option(
    "--as-toml/--as-dict",
    default=True,
    help="Display as original on-disk TOML or as the internal Python dictionary.",
)
@click.pass_obj
def settings(settings, as_toml):
    """
    Display the current settings.
    """
    click.secho(toml.dumps(settings) if as_toml else pprint.pformat(settings))


@cli.command()
@click.pass_obj
def login(settings):
    """
    Get a permanent token from Globus for initial setup.
    """
    try:
        refresh_token = acquire_refresh_token()
        logger.debug("Acquired refresh token")
    except globus_sdk.AuthAPIError as e:
        logger.error(f"Was not able to authorize due to error: {e}")
        error("Was not able to authorize", exit_code=AUTHORIZATION_ERROR)

    settings[AUTH][REFRESH_TOKEN] = refresh_token

    save_settings(settings)


@cli.group()
def bookmarks():
    """
    Subcommand group for managing endpoint bookmarks.
    """
    pass


@bookmarks.command()
@click.argument("bookmark")
@click.argument("endpoint")
@click.pass_obj
def add(settings, bookmark, endpoint):
    """
    Add a short name ("bookmark") for an endpoint.

    Once a bookmark is set, that name can be used in place of an endpoint id
    argument in any other command.
    """
    settings[BOOKMARKS][bookmark] = endpoint

    save_settings(settings)


@bookmarks.command()
@click.argument("bookmark")
@click.pass_obj
def rm(settings, bookmark):
    """
    Remove a bookmark.
    """
    settings[BOOKMARKS].pop(bookmark)

    save_settings(settings)


@bookmarks.command()
@click.pass_obj
def clear(settings):
    """
    Remove all bookmarks.
    """
    click.confirm(
        "Are you sure you want to delete all of your bookmarks?",
        abort=True,
        default=False,
    )

    settings[BOOKMARKS].clear()

    save_settings(settings)


BOOKMARKS_LS_COLUMN_ALIGNMENTS = {"endpoint": "ljust", "bookmark": "ljust"}


@bookmarks.command()
@click.pass_obj
def ls(settings):
    """
    List endpoint bookmarks.
    """
    rows = [{"bookmark": k, "endpoint": v} for k, v in settings[BOOKMARKS].items()]

    click.secho(
        table(
            headers=["bookmark", "endpoint"],
            rows=rows,
            header_fmt=BOLD_HEADER,
            alignment=BOOKMARKS_LS_COLUMN_ALIGNMENTS,
        )
    )


def endpoint_arg(*args, **kwargs):
    def _(func):
        return click.argument(
            *args, callback=_map_endpoint_through_bookmarks, **kwargs
        )(func)

    return _


def _map_endpoint_through_bookmarks(ctx, param, value):
    if value in ctx.obj[BOOKMARKS]:
        v = ctx.obj[BOOKMARKS][value]
        logger.debug(f"Found bookmark for endpoint {value} -> {v}")
        return v
    else:
        logger.debug(
            f"No bookmark for endpoint {value}, assuming it is an actual endpoint id"
        )
        return value


# ENDPOINT COMMANDS

DEFAULT_ENDPOINTS_HEADERS = ["id", "display_name"]
ENDPOINTS_COLUMN_ALIGNMENTS = {"id": "ljust", "display_name": "ljust"}


@cli.command()
@click.option("--limit", type=int, default=25, help="How many results to get.")
@click.pass_obj
def endpoints(settings, limit):
    """
    List endpoints.
    """
    tc = get_transfer_client_or_exit(settings[AUTH].get(REFRESH_TOKEN))

    endpoints = list(tc.endpoint_search(filter_scope="my-endpoints", num_results=limit))

    click.secho(
        table(
            headers=DEFAULT_ENDPOINTS_HEADERS,
            rows=endpoints,
            alignment=ENDPOINTS_COLUMN_ALIGNMENTS,
            header_fmt=BOLD_HEADER,
        )
    )

    click.secho("\nWeb View: https://app.globus.org/endpoints")


@cli.command()
@endpoint_arg("endpoint")
@click.pass_obj
def info(settings, endpoint):
    """
    Display full information about an endpoint.

    Although mostly intended for human consumption, the output is valid JSON.
    """
    tc = get_transfer_client_or_exit(settings[AUTH].get(REFRESH_TOKEN))

    info = EndpointInfo.get_or_exit(tc, endpoint)

    click.secho(str(info))


DEFAULT_HISTORY_HEADERS = [
    "task_id",
    "label",
    "status",
    "source_endpoint",
    "destination_endpoint",
    "completion_time",
]
HISTORY_COLUMN_ALIGNMENTS = {"task_id": "ljust", "label": "ljust"}


def history_style(row):
    fg = {"ACTIVE": "blue", "SUCCEEDED": "green", "FAILED": "red"}[row["status"]]

    return {"fg": fg}


@cli.command()
@click.option("--limit", type=int, default=25, help="How many results to get.")
@click.pass_obj
def history(settings, limit):
    """
    List transfer events.
    """
    tc = get_transfer_client_or_exit(settings[AUTH].get(REFRESH_TOKEN))
    tasks = [task.data for task in tc.task_list(num_results=limit)]
    for task in tasks:
        if task["label"] is None:
            task.pop("label")

    click.secho(
        table(
            headers=DEFAULT_HISTORY_HEADERS,
            rows=tasks,
            alignment=HISTORY_COLUMN_ALIGNMENTS,
            header_fmt=BOLD_HEADER,
            style=history_style,
        )
    )
    click.secho("\nWeb View: https://app.globus.org/activity?show=history")


DEFAULT_LS_HEADERS = ["DATA_TYPE", "name", "size"]
LS_COLUMN_ALIGNMENTS = {"DATA_TYPE": "ljust", "name": "ljust"}


@cli.command()
@endpoint_arg("endpoint")
@click.option(
    "--path",
    type=str,
    default="~/",
    help="The path to list the contents of. Defaults to '~/'.",
)
@click.pass_obj
def ls(settings, endpoint, path):
    """
    List the directory contents of a path on an endpoint.

    This command is intended to produce human-readable output. The "manifest"
    command is more useful as part of a workflow.
    """
    tc = get_transfer_client_or_exit(settings[AUTH].get(REFRESH_TOKEN))

    activate_endpoint_or_exit(tc, endpoint)

    entries = list(tc.operation_ls(endpoint, path=path))
    click.secho(
        table(
            headers=DEFAULT_LS_HEADERS,
            rows=entries,
            alignment=LS_COLUMN_ALIGNMENTS,
            header_fmt=BOLD_HEADER,
        )
    )


@cli.command()
@endpoint_arg("endpoint")
@click.option(
    "--path",
    type=str,
    default="~/",
    help="The path to list the contents of. Defaults to '~/'.",
)
@click.option(
    "--verbose/--compact",
    default=True,
    help="Whether the JSON representation should be verbose or compact. The default is verbose.",
)
@click.pass_obj
def manifest(settings, endpoint, path, verbose):
    """
    Print a JSON manifest of directory contents on an endpoint.

    The manifest can be printed in verbose, human-readable JSON or in compact,
    hard-for-humans JSON. Use --compact if you are worried about the size of
    the manifest. Otherwise, use --verbose (which is the default).
    """
    if verbose:
        json_dumps_kwargs = dict(indent=2)
    else:
        json_dumps_kwargs = dict(indent=None, separators=(",", ":"))

    tc = get_transfer_client_or_exit(settings[AUTH].get(REFRESH_TOKEN))

    activate_endpoint_or_exit(tc, endpoint)

    entries = list(tc.operation_ls(endpoint, path=path))
    click.secho(json.dumps(entries, **json_dumps_kwargs))


@cli.command()
@endpoint_arg("endpoint")
@click.pass_obj
def activate(settings, endpoint):
    """
    Activate a Globus endpoint.
    """
    tc = get_transfer_client_or_exit(settings[AUTH].get(REFRESH_TOKEN))

    activate_endpoint_or_exit(tc, endpoint)


# TRANSFER TASK COMMANDS


def wait_args(func):
    decorators = [
        click.option(
            "--timeout",
            type=int,
            default=60,
            help="How many seconds to fail a single attempt after. Defaults to 60 seconds.",
        ),
        click.option(
            "--interval",
            type=int,
            default=10,
            help="How often the task status is checked. Defaults to 10 seconds.",
        ),
        click.option(
            "--attempts",
            type=int,
            default=1,
            help="How many times to try waiting. Defaults to 1 attempt.",
        ),
    ]

    for d in reversed(decorators):
        func = d(func)

    return func


@cli.command()
@endpoint_arg("source_endpoint")
@endpoint_arg("destination_endpoint")
@click.argument("transfers", nargs=-1)
@click.option("--label", help="A label for the transfer.")
@click.option(
    "--sync-level",
    type=click.Choice(["exists", "size", "mtime", "checksum"], case_sensitive=False),
    default="checksum",
    help="How to decide whether to actually transfer a file or not. Defaults to checksum.",
)
@click.option(
    "--preserve-timestamps/--no-preserve-timestamps",
    default=True,
    help="Whether to preserve file modification timestamps. Defaults to preserve them.",
)
@click.option(
    "--verify-checksums/--no-verify-checksums",
    default=True,
    help="Whether to check that file checksums are the same at source and destination after transferring. Defaults to verify. Think very hard before turning this off.",
)
@click.option(
    "--wait", is_flag=True, help="If passed, wait for the transfer to complete."
)
@wait_args
@click.pass_obj
def transfer(
    settings,
    source_endpoint,
    destination_endpoint,
    transfers,
    label,
    sync_level,
    preserve_timestamps,
    verify_checksums,
    wait,
    timeout,
    interval,
    attempts,
):
    """
    Initiate a file transfer task.

    Transfer files from a source endpoint to a destination endpoint.
    The resulting task_id is printed to stdout.
    One invocation can include any number of transfer specifications, each of which
    can transfer a single file or an entire directory (recursively).

    Each transfer specification should be of the form

        /path/to/source/file:/path/to/destination/file

    If both paths end with a / the transfer is interpreted as a directory transfer.
    If neither ends with a / it is a single file transfer.
    (Both paths must either end or not end with /, mixing them is an error.)
    Paths should be absolute; to expand the user's home directory on either
    side, wrap the transfer specification in single quotes to prevent local
    variable expansion:

        '~/path/to/source/dir/':'~/path/to/destination/dir/'

    The synchronization level determines whether individual files are actually
    transferred, as follows:

        exists: if the destination file is absent.

        size: if destination file size does not match the source.

        mtime: if the source file has a newer modified time than the destination file.

        checksum: if the checksum of the contents of the source and destination files differ.

    The default synchronization level is checksum. Stricter levels imply
    less-strict levels (i.e., checksum synchronization implies existence checking).

    If --wait is passed, this command will also wait for the task to finish
    instead of immediately returning
    (see the wait command itself for the semantics of this mode and descriptions
    of the accompanying options; run "globus wait --help").
    """
    tc = get_transfer_client_or_exit(settings[AUTH].get(REFRESH_TOKEN))

    tdata = globus_sdk.TransferData(
        tc,
        source_endpoint,
        destination_endpoint,
        label=label,
        sync_level=sync_level,
        preserve_timestamp=preserve_timestamps,
        verify_checksum=verify_checksums,
    )
    for t in transfers:
        src, dst = t.split(":")
        if src[-1] == dst[-1] == "/":  # directory -> directory
            logger.debug(f"Transfer directory {src} -> {dst}")
            tdata.add_item(src, dst, recursive=True)
        elif src[-1] == "/" or dst[-1] == "/":  # malformed directory transfer
            logger.error(f"Invalid transfer specification: {t}")
            error(
                f"Invalid transfer specification '{t}' (if transferring directories, both paths must end with /)",
                exit_code=INVALID_TRANSFER_SPECIFICATION_ERROR,
            )
        else:  # file -> file
            logger.debug(f"Transfer file {src} -> {dst}")
            tdata.add_item(src, dst)

    activate_endpoint_or_exit(tc, source_endpoint)
    activate_endpoint_or_exit(tc, destination_endpoint)

    result = tc.submit_transfer(tdata)
    task_id = result["task_id"]

    if wait:
        wait_for_task_or_exit(
            transfer_client=tc,
            task_id=task_id,
            timeout=timeout,
            interval=interval,
            max_attempts=attempts,
        )

    click.secho(task_id)


# TODO: how do we check for transfer errors? e.g., directories without trailing slashes, path not existing, etc.


@cli.command()
@click.argument("task_id")
@click.pass_obj
def cancel(settings, task_id):
    """
    Cancel a task.
    """
    tc = get_transfer_client_or_exit(settings[AUTH].get(REFRESH_TOKEN))

    try:
        result = tc.cancel_task(task_id)
    except globus_sdk.TransferAPIError as e:
        logger.exception(f"Task {task_id} was not successfully cancelled")
        error(
            f"Task {task_id} was not successfully cancelled: {e.message}",
            exit_code=CANCEL_TASK_ERROR,
        )

    if result["code"] == "Cancelled":
        click.secho(f"Task {task_id} has been successfully cancelled", fg="green")
    else:
        logger.error(f"Task {task_id} was not successfully cancelled:\n{result}")
        error(
            f"Task {task_id} was not successfully cancelled:\n{result}",
            exit_code=CANCEL_TASK_ERROR,
        )


@cli.command()
@click.argument("task_id")
@wait_args
@click.pass_obj
def wait(settings, task_id, timeout, interval, attempts):
    """
    Wait for a task to complete.
    """
    tc = get_transfer_client_or_exit(settings[AUTH].get(REFRESH_TOKEN))

    wait_for_task_or_exit(
        transfer_client=tc,
        task_id=task_id,
        timeout=timeout,
        interval=interval,
        max_attempts=attempts,
    )

    click.secho(task_id)


# CLI HELPERS


def setup_logging(verbose):
    if verbose >= 1:
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s ~ %(levelname)s ~ %(name)s:%(lineno)d ~ %(message)s"
            )
        )
        logger.addHandler(handler)

    if verbose >= 2:
        globus_logger = logging.getLogger("globus_sdk")
        globus_logger.setLevel(logging.DEBUG)
        globus_logger.addHandler(handler)


def get_transfer_client_or_exit(refresh_token):
    if refresh_token is None:
        logger.error(f"No refresh token found in settings.")
        error(
            f"Was not able to find a refresh token; have you run 'globus login'?",
            exit_code=AUTHORIZATION_ERROR,
        )

    client = get_client()
    authorizer = globus_sdk.RefreshTokenAuthorizer(refresh_token, client)
    return globus_sdk.TransferClient(authorizer=authorizer)


def activate_endpoint_or_exit(transfer_client, endpoint):
    success = (
        EndpointInfo.get_or_exit(transfer_client, endpoint).is_active
        or activate_endpoint_automatically(transfer_client, endpoint)
        or activate_endpoint_manually(transfer_client, endpoint)
    )
    if not success:
        msg = f"Was not able to activate endpoint {endpoint}"
        logger.error(msg)
        error(msg, exit_code=ENDPOINT_ACTIVATION_ERROR)

    expires_in = EndpointInfo.get_or_exit(
        transfer_client, endpoint
    ).activation_expires_in
    logger.info(f"Activation of endpoint {endpoint} will expire in {expires_in}")
    return True


def wait_for_task_or_exit(
    transfer_client, task_id, timeout, interval=10, max_attempts=1
):
    attempts = 0
    done = False
    errored = False
    while True:
        attempts += 1
        logger.debug(
            f"Attempting to wait for task {task_id} [attempt {attempts}/{max_attempts}]"
        )
        try:
            done = transfer_client.task_wait(
                task_id, timeout=timeout, polling_interval=interval
            )
        except globus_sdk.TransferAPIError as e:
            logger.exception(f"Could not wait for task {task_id}.")
            warning(f"Could not wait for task {task_id} due to error: {e.message}")
            errored = True

        if done:
            return done

        logger.debug(f"Attempt {attempts} to wait for task {task_id} failed")

        if attempts >= max_attempts:
            msg = f"Timed out waiting for task {task_id} after {attempts} attempts."
            logger.error(msg)
            error(msg, exit_code=WAIT_TASK_TIMEOUT if not errored else WAIT_TASK_ERROR)


def table(
    headers, rows, fill="", header_fmt=None, row_fmt=None, alignment=None, style=None
):
    if header_fmt is None:
        header_fmt = lambda _: _
    if row_fmt is None:
        row_fmt = lambda _: _
    if alignment is None:
        alignment = {}
    if style is None:
        style = lambda _: {}

    headers = tuple(headers)
    lengths = [len(str(h)) for h in headers]

    align_methods = [alignment.get(h, "center") for h in headers]

    processed_rows = []
    for row in rows:
        processed_rows.append([str(row.get(key, fill)) for key in headers])

    for row in processed_rows:
        lengths = [max(curr, len(entry)) for curr, entry in zip(lengths, row)]

    header = header_fmt(
        "  ".join(
            getattr(str(h), a)(l) for h, l, a in zip(headers, lengths, align_methods)
        ).rstrip()
    )

    lines = [
        click.style(
            row_fmt(
                "  ".join(
                    getattr(f, a)(l) for f, l, a in zip(row, lengths, align_methods)
                )
            ),
            **style(original_row),
        )
        for original_row, row in zip(rows, processed_rows)
    ]

    output = "\n".join([header] + lines)

    return output


def warning(msg):
    click.secho(f"Warning: {msg}", err=True, fg="yellow")


def error(msg, exit_code=1):
    click.secho(f"Error: {msg}", err=True, fg="red")
    sys.exit(exit_code)


# BACKEND


def get_client():
    return globus_sdk.NativeAppAuthClient(CLIENT_ID)


def acquire_refresh_token():
    client = get_client()
    client.oauth2_start_flow(refresh_tokens=True)

    click.secho(f"Go to this URL and login: {client.oauth2_get_authorize_url()}")
    auth_code = click.prompt(
        "Copy the code you get after login here and press enter"
    ).strip()

    token_response = client.oauth2_exchange_code_for_tokens(auth_code)

    globus_transfer_data = token_response.by_resource_server["transfer.api.globus.org"]

    return globus_transfer_data["refresh_token"]


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


class EndpointInfo:
    def __init__(self, response):
        self._response = response

    def __str__(self):
        return str(self._response)

    @classmethod
    def get_or_exit(cls, transfer_client, endpoint):
        try:
            response = transfer_client.get_endpoint(endpoint)
        except globus_sdk.TransferAPIError as e:
            logger.exception(f"Could not get endpoint info")
            error(
                f"Was not able to get endpoint info due to error: {e.message}",
                exit_code=ENDPOINT_INFO_ERROR,
            )

        return cls(response)

    def __getitem__(self, item):
        return self._response[item]

    @property
    def id(self):
        return self["id"]

    @property
    def is_active(self):
        return self["activated"] is True

    @property
    def activation_expires_in(self):
        return datetime.timedelta(seconds=self["expires_in"])


def activate_endpoint_automatically(transfer_client, endpoint):
    response = transfer_client.endpoint_autoactivate(endpoint)

    return response["code"] != "AutoActivationFailed"


def activate_endpoint_manually(transfer_client, endpoint):
    query_string = urlencode(
        {"origin_id": EndpointInfo.get_or_exit(transfer_client, endpoint).id}
    )
    click.secho(
        f"Endpoint requires manual activation, please open the following URL in a browser to activate the endpoint: https://app.globus.org/file-manager?{query_string}"
    )
    click.confirm("Press ENTER after activating the endpoint...", show_default=False)
    return EndpointInfo.get_or_exit(transfer_client, endpoint).is_active


if __name__ == "__main__":
    cli()
