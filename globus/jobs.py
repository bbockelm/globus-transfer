import logging
import os
from pathlib import Path
import getpass
import datetime

from . import constants
from .uilts import is_interactive

import htcondor
import classad
from htchirp import HTChirp

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_globus_jobs(user=None):
    if user is None:
        user = getpass.getuser()

    schedd = htcondor.Schedd()
    constraint = f"IsGlobusJob && Owner == {classad.quote(user)}"
    logger.debug(f"Performing query with constraint {constraint}")
    return [Job(ad) for ad in schedd.query(constraint)]


class Job:
    def __init__(self, ad: classad.ClassAd):
        self._ad = ad

    def __getitem__(self, item):
        return self._ad[item]

    def get(self, item, default=None):
        return self._ad.get(item, default)

    def items(self):
        yield from self._ad.items()

    def keys(self):
        yield from self._ad.keys()

    def values(self):
        yield from self._ad.values()

    def __str__(self):
        return str(self._ad)

    @property
    def cluster_id(self):
        return self._ad["ClusterId"]

    @property
    def proc_id(self):
        return self._ad["ProcId"]

    @property
    def is_cron(self):
        return any(
            self._ad.get(k, False)
            for k in [
                "CronMinute",
                "CronHour",
                "CronDayOfMonth",
                "CronMonth",
                "CronDayOfWeek",
            ]
        )

    @property
    def submitted_at(self):
        return datetime.datetime.fromtimestamp(self._ad["QDate"]).astimezone(
            datetime.timezone.utc
        )

    @property
    def status_last_changed_at(self):
        return datetime.datetime.fromtimestamp(
            self._ad["EnteredCurrentStatus"]
        ).astimezone(datetime.timezone.utc)

    @property
    def status(self):
        return constants.JOB_STATUS[self._ad["JobStatus"]]

    @property
    def is_held(self):
        return self.status == "HELD"

    @property
    def hold_reason(self):
        return self._ad["HoldReason"]

    @property
    def universe(self):
        return constants.UNIVERSE[self._ad["JobUniverse"]]

    @property
    def stdout(self):
        p = Path(self._ad["Out"])
        if not p.is_absolute():
            return (Path(self._ad["Iwd"]) / self._ad["Out"]).absolute()
        return p

    @property
    def stderr(self):
        p = Path(self._ad["Err"]).absolute()
        if not p.is_absolute():
            return (Path(self._ad["Iwd"]) / self._ad["Err"]).absolute()
        return p

    @property
    def log(self):
        return Path(self._ad["UserLog"]).absolute()


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
