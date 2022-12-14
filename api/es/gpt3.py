"""
Module designated for the ELK API service to communicate and exchange information with
the GPT-3 service.
"""

import requests
import json
import time
from colorama import Fore

from errors.elastic_err import ElasticError
from settings.settings import GPT3_SERVER, GPT3_PORT


class GPT3Request(object):
    """
    Class designated to handle the communications between the ELK and GPT-3 services.
    """

    def __init__(self, question: str, context: str):
        self.logger = ElasticError(__file__, self.__class__.__name__)
        try:
            start = time.time()
            self.res = requests.post("http://" + GPT3_SERVER + ":" + str(
                GPT3_PORT) + "/question", data=json.dumps({"question": question, "context": context}))
        except Exception as err:
            self.logger.msg = "Something went wrong when trying to call the GPT-3 service!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger
        else:
            # Response OK?
            if self.res.ok:
                # Decode response
                self.results = self.res.content.decode('utf-8')
                # Check response content and type
                self.logger.msg = "Response from GPT-3 service: {}".format(
                    self.results)
                self.logger.info(extra_msg="Type: {}".format(
                    type(self.results).__name__))
                # String?
                if type(self.results).__name__ == 'str':
                    self.results = self.results.split('":"')[1][:-2]
                # Dict?
                elif type(self.results).__name__ == 'dict':
                    self.results = self.results['data']

            else:
                self.logger.msg = "Response from <OUR> GPT-3 service NOT OK!"
                self.logger.error(extra_msg="Code received: {}".format(
                    str(self.res.status_code)))
                raise self.logger
            end = time.time()
            finish = str(end - start)
            finish = finish.split(".")[0] + "." + finish.split(".")[1][:-2]
            self.logger.msg = "GPT-3 algorithm took {} seconds".format(
                Fore.LIGHTCYAN_EX + finish + Fore.RESET)
            self.logger.info()

    def __str__(self):
        return self.results
