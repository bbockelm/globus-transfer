import logging
import os
from pathlib import Path
import getpass

from . import constants
from .uilts import is_interactive

import htcondor
import classad
from htchirp import HTChirp

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_globus_job_ads(user=None):
    if user is None:
        user = getpass.getuser()

    schedd = htcondor.Schedd()
    return schedd.query(f"IsGlobusJob && Owner == {user}")


def set_job_attr(key, value, scratch_ad=None):
    if scratch_ad is None:
        if is_interactive():
            raise ValueError(
                "Setting a job attribute while not in a job requires a scratch ad."
            )

        scratch_ad = classad.parseOne(
            (Path(os.environ["_CONDOR_SCRATCH_DIR"]) / ".job.ad").read_text()
        )

    UNIVERSE_TO_SET_ATTR[scratch_ad["JobUniverse"]](scratch_ad, key, value)

    logger.debug(f"Set job attribute {key} = {value}")


def _set_job_attr_vanilla_universe(scratch_job_ad, key, value):
    with HTChirp() as chirp:
        chirp.set_job_attr(key, value)


def _set_job_attr_local_universe(scratch_job_ad, key, value):
    schedd = htcondor.Schedd()
    constraint = f"ClusterID == {scratch_job_ad['ClusterId']}"
    logger.debug(f"Calling edit with constraint {constraint} to set {key} = {value}")
    schedd.edit(constraint, key, value)


UNIVERSE_TO_SET_ATTR = {
    constants.VANILLA_UNIVERSE: _set_job_attr_vanilla_universe,
    constants.LOCAL_UNIVERSE: _set_job_attr_local_universe,
}
