"""
Module meant to handle most of the request/response work
when it comes to sending/receiving data through the API.
"""
import requests

from errors.data_err import DataError


class DataRequest(object):
    """
    Class designated to handle most requests when it comes to
    ELK API's ability to communicate with other services.
    """

    def __init__(self, **kwargs):
        """
        This method will look for either of these attributes:\n
        1. `url <str>`
        2. `host <str>` and `port <str>/<int>`
        """
        self.logger = DataError(__file__, self.__class__.__name__)
        self.data = self._get_data()

        # Checking the keys in **kwargs for the ones we expect
        available_keys = kwargs.keys()
        if 'url' not in available_keys \
                or ('host' not in available_keys
                    and 'port' not in available_keys):

            self.logger.msg = "No ['url'] or ['host' & 'port'] keys in kwargs!"
            self.logger.error(extra_msg="Available keys:\n\t{}".format(
                "\n\t".join(available_keys)))
            raise self.logger

        # Parse 'url' value
        url = kwargs.get('url', None)
        if isinstance(url, str) and len(url) > 7:
            try:
                if url.startswith('http://'):
                    url = url[7:]
                host, port = \
                    str(kwargs['url']).split(':', )[0], \
                    str(kwargs['url']).split(':')[1]

            except Exception as err:
                self.logger.msg = "Could not detect any colon ':' within the 'url' parameter!"
                self.logger.error(
                    "Original value: {}".format(kwargs.get('url')))
                raise self.logger

            else:
                self.response = requests.post(
                    host + ':' + port, data=self.data)

        # No 'url'?
        # Look for 'host' and 'port'
        else:
            host = kwargs.get('host', None)
            port = kwargs.get('port', None)
            if not host or not len(host) > 7 or not port or not str(port).isdigit():
                self.logger.msg = "'host' or 'port' values unacceptable!"
                self.logger.error(
                    extra_msg="Expected from 'host':\n\t1. Not 'None'\n\t2. Longer than 7 characters long.\nGot: {}".format(host))
                self.logger.error(
                    extra_msg="Expected from 'host':\n\t1. Not 'None'\n\t2. Must be convertable into a digit.\nGot: {}".format(port))
                raise self.logger

            self.response = requests.post(host + ':' + port, data=self.data)

    def _get_data(self):
        """
        Method that handles data retrieval to later submit to
        Claude's OOV service.
        """
        return dict()
