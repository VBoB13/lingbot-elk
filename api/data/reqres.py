"""
Module meant to handle most of the request/response work
when it comes to sending/receiving data through the API.
"""
import os

import requests

from settings.settings import DATA_DIR
from errors.data_err import DataError


class DataRequest(object):
    """
    Class designated to handle most requests when it comes to
    ELK API's ability to communicate with other services.
    """

    def __init__(self, data_func=None, method: str = 'get', *args, **kwargs):
        """
        Parameters:
        `data_func <str>`: function that returns a string value.
        `*args <Any>`: arguments passed
        This method will look for either of these attributes in **kwargs:\n
        1. `url <str>`
        2. `host <str>` and `port <str>/<int>`
        """
        self.method_func = self._get_method(method)
        self.logger = DataError(__file__, self.__class__.__name__)
        self.server = self._get_server(**kwargs)
        self.data = self._get_data(data_func, *args)
        if method == 'get':
            self.response = self.method_func(
                self.server, params={"q": self.data})
        else:
            self.response = self.method_func(self.server, data=self.data)

    def _get_data(self, data_func=None, *args) -> str:
        """
        Method that handles data retrieval to later submit to
        Claude's OOV service.
        """
        # If provided a data collecting function
        # we simply return the value of that function
        if data_func is not None and callable(data_func):
            try:
                return data_func(*args)
            except Exception as err:
                self.logger.msg = "Something went wrong during execution of function '{}'!".format(
                    data_func.__name__)
                self.logger.error(extra_msg=str(err), orgErr=err)
                raise self.logger

        # Otherwise, we get data from our .txt file
        return self._get_data_from_file()

    def _get_data_from_file(self) -> str:
        """
        Method designed to fetch data from the local ./data/oov/material.txt file.
        """

        text_file = os.path.join(DATA_DIR, 'oov') + '/material.txt'
        file_content = None
        try:
            with open(text_file, 'r') as file:
                file_content = "".join(file.readlines())

        except Exception as err:
            self.logger.msg = "Could not open .txt to extract data!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger

        else:
            if file_content is None:
                self.logger.msg = "No content in .txt file!"
                self.logger.error()
                raise self.logger

        return file_content

    def _get_method(self, method: str) -> function:
        if method == 'delete':
            return requests.delete
        elif method == 'post':
            return requests.post
        else:
            return requests.get

    def _get_server(self, **kwargs):
        """
        Method designed to make sure objects are initialized
        with a properly formatted `self.server <str>` attribute.
        """
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
                    server = url[7:]
                else:
                    server = url

            except Exception as err:
                self.logger.msg = "Could not detect any colon ':' within the 'url' parameter!"
                self.logger.error(extra_msg="Original value: {}".format(
                    kwargs.get('url')), orgErr=err)
                raise self.logger

            server += '/simplesegment'

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

            server = host + ':' + port

        return server
