import logging
import sys

import click
from click_didyoumean import DYMGroup

import globus_sdk

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)

AUTH_ERROR = 1

CLIENT_ID = "fbb557b2-aa0b-42e9-9a07-04c5c4f01474"

# CLI

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS, cls=DYMGroup)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show log messages as the CLI runs.",
)
def cli(verbose):
    if verbose:
        _setup_logger()
    logger.debug(f'{sys.argv[0]} called with arguments "{" ".join(sys.argv[1:])}"')


def _setup_logger():
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s ~ %(levelname)s ~ %(name)s:%(lineno)d ~ %(message)s"
        )
    )

    logger.addHandler(handler)


@cli.command()
def endpoints():
    for ep in get_transfer_client().endpoint_search(filter_scope="my-endpoints"):
        click.echo("[{}] {}".format(ep["id"], ep["display_name"]))


@cli.command()
@click.option("--limit", type=int, default=25, help="How many results to get.")
def history(limit):
    for task in get_transfer_client().task_list(
        num_results=limit, filter="type:TRANSFER,DELETE"
    ):
        print(task["task_id"], task["type"], task["status"])


# BACKEND


def acquire_auth_and_transfer_data():
    client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
    client.oauth2_start_flow(refresh_tokens=True)

    click.echo(f"Go to this URL and login: {client.oauth2_get_authorize_url()}")
    auth_code = click.prompt("Copy the code you get after login here").strip()

    token_response = client.oauth2_exchange_code_for_tokens(auth_code)

    globus_auth_data = token_response.by_resource_server["auth.globus.org"]
    globus_transfer_data = token_response.by_resource_server["transfer.api.globus.org"]

    return globus_auth_data, globus_transfer_data


def make_transfer_client(transfer_token):
    # TODO: refresh tokens
    authorizer = globus_sdk.AccessTokenAuthorizer(transfer_token)
    return globus_sdk.TransferClient(authorizer=authorizer)


def get_transfer_client():
    try:
        auth_data, transfer_data = acquire_auth_and_transfer_data()
        logger.debug("Acquired transfer token")
    except globus_sdk.AuthAPIError as e:
        logger.error(f"Was not able to authorize {e.args[-1]}", file=sys.stderr)
        click.echo(f"ERROR: was not able to authorize", err=True)
        sys.exit(AUTH_ERROR)

    return make_transfer_client(transfer_data["access_token"])


if __name__ == "__main__":
    cli()
