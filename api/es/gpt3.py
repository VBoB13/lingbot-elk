"""
Module designated for the ELK API service to communicate and exchange information with
the GPT-3 service.
"""

import requests
from urllib import parse

from errors.elastic_err import ElasticError
from settings.settings import GPT3_SERVER, GPT3_PORT


class GPT3Request(object):
    """
    Class designated to handle the communications between the ELK and GPT-3 services.
    """

    def __init__(self, question: str, context: str):
        self.logger = ElasticError(__file__, self.__class__.__name__)
        try:
            self.res = requests.get("http://" + GPT3_SERVER + ":" + str(
                GPT3_PORT) + "/question?" + parse.quote_plus({"question": question, "context": context}))
        except Exception as err:
            self.logger.msg = "Something went wrong when trying to call the GPT-3 service!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger
        else:
            if self.res.ok:
                self.results = self.res["data"]["choices"][0]["text"]
            else:
                self.logger.msg = "Response from <OUR> GPT-3 service NOT OK!"
                self.logger.error(extra_msg="Code received: {}".format(
                    str(self.res.status_code)))
                raise self.logger

    def __str__(self):
        return self.results
