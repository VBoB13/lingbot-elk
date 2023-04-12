"""
Module designated for the ELK API service to communicate and exchange information with
the GPT-3 service.
"""

import requests
from requests import Response
import json
import time
from colorama import Fore

from errors.errors import ElasticError
from settings.settings import GPT3_SERVER, GPT3_PORT


class GPT3Base(object):
    def __init__(self):
        self.logger = ElasticError(__file__, self.__class__.__name__)

    def get_gpt3_response(self, format: bool = True):
        # Annotating the type of [self.res]
        self.res: Response
        if not self.res.ok:
            self.logger.msg = "Response from <OUR> GPT-3 service NOT OK!"
            self.logger.error(extra_msg="Code received: {}".format(
                str(self.res.status_code)))
            raise self.logger

        if format:
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
            self.results = self.res.json()["data"]


class GPT3Request(GPT3Base):
    """
    Class designated to handle the communications between the ELK and GPT-3 services.
    """

    def __init__(self, question: str, context: str, vendor_id: str, gpt3_strict: bool, session_id: str = "test_session"):
        super().__init__()
        try:
            start = time.time()
            self.res = requests.post("http://" + GPT3_SERVER + ":" + str(
                GPT3_PORT) + "/question", data=json.dumps({"question": question, "context": context, "vendor_id": vendor_id, "strict": gpt3_strict, "session_id": session_id}))
        except Exception as err:
            self.logger.msg = "Something went wrong when trying to call the GPT-3 service!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger
        else:
            try:
                self.get_gpt3_response()
            except Exception as err:
                self.logger.msg = ""
            end = time.time()
            finish = str(round(end - start, 2))
            self.logger.msg = "GPT-3 algorithm took {} seconds".format(
                Fore.LIGHTCYAN_EX + finish + Fore.RESET)
            self.logger.info()

    def __str__(self):
        return self.results


class GPT3UtilityRequest(GPT3Base):
    """
    Class designated to handle the communications between the ELK and GPT-3 services while also solving extraction problems.
    \nParams:\n
    `service`: Variable that should consist of `[service]:[subservice]` string definitions.
    `[service]` can be: `extract`.
    `[subservice]` can be: `entities`, `event-name`, `event-price`, `date` or `accommodation`
    """

    services = {
        "extract": ['entities', 'keywords'],
        "analyze": ['sentiment'],
        "intent": ['flight', 'hotel']
    }

    def __init__(self, text: str, service: str = "extract:entities"):
        super().__init__()
        try:
            self.text = text
            self.base_address = "http://" + GPT3_SERVER + ":" + str(GPT3_PORT)
            self.service = service.split(":")[0]
            self.subservice = service.split(":")[1]

            # When we DONT find the service that we allow
            if self.subservice not in self.services[self.service]:
                self.logger.msg = "GPT3 extraction services include: %s" % str(
                    ["extract-" + service for service in self.services["extract"]])
                self.logger.error(extra_msg="Got: %s" %
                                  str(self.service + "-" + self.subservice))
                raise self.logger
            # Set request address to be the service that is to be executed
            self.address = self.base_address + "/" + self.service + "-" + self.subservice
        except Exception as err:
            self.logger.msg = "Something went wrong when trying to call the GPT-3 service!"
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err
        else:
            try:
                # No troubles? .egg-see-cute :)
                self._decide_service()
            except Exception as err:
                self.logger.msg = "Something went wrong when trying to send/receive request from GPT3 service!"
                self.logger.error(extra_msg=str(err), orgErr=err)
                raise self.logger from err

    def __str__(self):
        return self.results

    def _decide_service(self):
        """
        Chooses which service to execute based on the
        1. `self.service`\n
        2. `self.subservice`\n
        provided. Different methods gets executed based on these attribute values.
        """
        entities = []
        if len(self.text) > 0 and isinstance(self.text, str):
            self.logger.msg = "Asking GPT3 service to execute service: %s" % str(
                self.service + ":" + self.subservice)
            self.logger.info()

            # Differentiating the services & their behavior
            if self.service == 'intent' and self.subservice == 'flight':
                entities = ['Departure airport', 'Departure date',
                            'Destination airport', 'Return date']

            data = {"text": self.text}
            if len(entities) > 0:
                data.update({"entities": entities})

            # Making the actual request
            self.res = requests.post(self.address, data=json.dumps(data))
            # Base class method
            self.get_gpt3_response(format=False)
