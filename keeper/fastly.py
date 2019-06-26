"""Lightweight library of Fastly API interactions needed by LTD Keeper.

See https://docs.fastly.com/api/ for more information about the Fastly API.
"""

from structlog import get_logger
import requests

from .exceptions import FastlyError


class FastlyService(object):
    """API client for a Fastly service.

    Parameters
    ----------
    service_id : str
        The Fastly service ID.
    api_key : str
        The Fastly API key. We only support key-based authentication.
    """

    def __init__(self, service_id, api_key):
        super(FastlyService, self).__init__()
        self.service_id = service_id
        self.api_key = api_key
        self._api_root = 'https://api.fastly.com'
        self._logger = get_logger(__name__)

    def _url(self, path):
        return self._api_root + path

    def purge_key(self, surrogate_key):
        """Instant purge URLs with a given `surrogate_key`.

        See
        https://docs.fastly.com/api/purge#purge_077dfb4aa07f49792b13c87647415537
        for more information.
        """
        path = '/service/{service}/purge/{surrogate_key}'.format(
            service=self.service_id, surrogate_key=surrogate_key)
        self._logger.info(
            'Fastly key purge',
            path=path, surrogate_key=surrogate_key)
        r = requests.post(self._url(path),
                          headers={'Fastly-Key': self.api_key,
                                   'Accept': 'application/json'})
        if r.status_code != 200:
            raise FastlyError(r.json)
