import logging
import datetime

import globus_sdk


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
            raise e

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
