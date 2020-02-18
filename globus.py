import logging
import sys
from pathlib import Path
from urllib.parse import urlencode

import click
from click_didyoumean import DYMGroup

import globus_sdk

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

AUTHORIZATION_ERROR = 1
ACTIVATION_ERROR = 1
INVALID_TRANSFER_SPECIFICATION_ERROR = 1

CLIENT_ID = "fbb557b2-aa0b-42e9-9a07-04c5c4f01474"

REFRESH_TOKEN_PATH = Path.home() / ".globus_refresh_token"

# CLI

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS, cls=DYMGroup)
@click.option(
    "--verbose", "-v", count=True, default=0, help="Show log messages as the CLI runs."
)
def cli(verbose):
    setup_logging(verbose)
    logger.debug(f'{sys.argv[0]} called with arguments "{" ".join(sys.argv[1:])}"')


@cli.command()
def login():
    try:
        refresh_token = acquire_refresh_token()
        logger.debug("Acquired refresh token")
    except globus_sdk.AuthAPIError as e:
        logger.error(f"Was not able to authorize {e.args[-1]}")
        click.echo(f"ERROR: was not able to authorize", err=True)
        sys.exit(AUTHORIZATION_ERROR)

    write_refresh_token(refresh_token)


@cli.command()
@click.option("--limit", type=int, default=25, help="How many results to get.")
def endpoints(limit):
    tc = get_transfer_client()
    for ep in tc.endpoint_search(filter_scope="my-endpoints", num_results=limit):
        click.echo("[{}] {}".format(ep["id"], ep["display_name"]))


@cli.command()
@click.option("--limit", type=int, default=25, help="How many results to get.")
def history(limit):
    tc = get_transfer_client()
    for task in tc.task_list(num_results=limit, filter="type:TRANSFER,DELETE"):
        click.echo(
            f'{task["task_id"]} {task["label"] or ""} {task["type"]} {task["status"]}'
        )


@cli.command()
@click.argument("endpoint")
@click.option("--path", type=str, default="~/")
def ls(endpoint, path):
    tc = get_transfer_client()

    activate_endpoint_or_exit(tc, endpoint)

    for entry in tc.operation_ls(endpoint, path=path):
        click.echo(f"{entry['name']} {entry['type']}")


@cli.command()
@click.argument("source_endpoint")
@click.argument("destination_endpoint")
@click.argument("transfers", nargs=-1)
@click.option("--label", help="The label for the transfer.")
def transfer(source_endpoint, destination_endpoint, transfers, label):
    tc = get_transfer_client()

    tdata = globus_sdk.TransferData(
        tc, source_endpoint, destination_endpoint, label=label, sync_level="checksum"
    )
    for t in transfers:
        src, dst = t.split(":")
        if src[-1] == dst[-1] == "/":  # directory -> directory
            logger.debug(f"Transfer directory {src} -> {dst}")
            tdata.add_item(src, dst, recursive=True)
        elif src[-1] == "/" or dst[-1] == "/":  # malformed directory transfer
            logger.error(f"Invalid transfer specification: {t}")
            click.echo(
                f"ERROR: invalid transfer specification '{t}' (if transferring directories, both paths must end with /)",
                err=True,
            )
            sys.exit(INVALID_TRANSFER_SPECIFICATION_ERROR)
        else:  # file -> file
            logger.debug(f"Transfer file {src} -> {dst}")
            tdata.add_item(src, dst)

    activate_endpoint_or_exit(tc, source_endpoint)
    activate_endpoint_or_exit(tc, destination_endpoint)

    result = tc.submit_transfer(tdata)

    click.echo(f"Transfer task id is {result['task_id']}")


# TODO: how do we check for transfer errors? e.g., directories without trailing slashes, path not existing, etc.

# CLI HELPERS


def setup_logging(verbose):
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s ~ %(levelname)s ~ %(name)s:%(lineno)d ~ %(message)s"
        )
    )

    if verbose >= 1:
        logger.addHandler(handler)

    if verbose >= 2:
        globus_logger = logging.getLogger("globus_sdk")
        globus_logger.setLevel(logging.DEBUG)
        globus_logger.addHandler(handler)


def activate_endpoint_or_exit(transfer_client, endpoint):
    success = (
        is_endpoint_active(transfer_client, endpoint)
        or activate_endpoint_automatically(transfer_client, endpoint)
        or activate_endpoint_manually(transfer_client, endpoint)
    )
    if not success:
        logger.error(f"Was not able to activate endpoint {endpoint}")
        click.echo(f"ERROR: was not able to activate endpoint {endpoint}", err=True)
        sys.exit(ACTIVATION_ERROR)


# BACKEND


def get_client():
    return globus_sdk.NativeAppAuthClient(CLIENT_ID)


def acquire_refresh_token():
    client = get_client()
    client.oauth2_start_flow(refresh_tokens=True)

    click.echo(f"Go to this URL and login: {client.oauth2_get_authorize_url()}")
    auth_code = click.prompt("Copy the code you get after login here").strip()

    token_response = client.oauth2_exchange_code_for_tokens(auth_code)

    globus_transfer_data = token_response.by_resource_server["transfer.api.globus.org"]

    return globus_transfer_data["refresh_token"]


def write_refresh_token(refresh_token, path=None):
    if path is None:
        path = REFRESH_TOKEN_PATH

    path.write_text(refresh_token)
    logger.debug(f"Wrote refresh token to {path}")

    return path


def read_refresh_token(path=None):
    if path is None:
        path = REFRESH_TOKEN_PATH

    token = REFRESH_TOKEN_PATH.read_text().strip()
    logger.debug(f"Read refresh token from {path}")

    return token


def get_transfer_client():
    refresh_token = read_refresh_token()
    client = get_client()
    authorizer = globus_sdk.RefreshTokenAuthorizer(refresh_token, client)
    return globus_sdk.TransferClient(authorizer=authorizer)


def get_endpoint_info(transfer_client, endpoint):
    return transfer_client.get_endpoint(endpoint)


def is_endpoint_active(transfer_client, endpoint):
    return get_endpoint_info(transfer_client, endpoint)["activated"] is True


def activate_endpoint_automatically(transfer_client, endpoint):
    response = transfer_client.endpoint_autoactivate(endpoint)

    return response["code"] != "AutoActivationFailed"


def activate_endpoint_manually(transfer_client, endpoint):
    query_string = urlencode(
        {"origin_id": get_endpoint_info(transfer_client, endpoint)["id"]}
    )
    click.echo(
        f"Endpoint requires manual activation, please open the following URL in a browser to activate the endpoint: https://app.globus.org/file-manager?{query_string}"
    )
    click.confirm("Press ENTER after activating the endpoint...")
    return is_endpoint_active(transfer_client, endpoint)


if __name__ == "__main__":
    cli()
