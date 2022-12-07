"""
Module meant to be used as a shortcut to generate new words through
Claude's OOV service, take the newly generated new terms, words and phrases
and feed them into the ik_smart analyer's dictionairy files (.dic)
"""
from colorama import Fore

from data import CLAUDE_TEST_SERVER, OOV_PORT
from data.reqres import DataRequest
from errors.data_err import DataError
from es.elastic import LingtelliElastic
from helpers.interactive import question_check
from settings.settings import DIC_DIR, DIC_FILE


class OOVService(object):
    """
    Class meant to handle OOV service tasks.
    """

    def __init__(self, text: str = None):
        self.logger = DataError(__file__, self.__class__.__name__)
        self.server = CLAUDE_TEST_SERVER + ":" + str(OOV_PORT)

        self.results = self._run(text)
        self._save_results()

    def _return_text(self, text: str) -> str:
        """
        Method meant to just be a method for the sake of 
        workflow consistency with DataRequests's data_func.
        """
        return text

    def _run(self, text: str = None):
        """
        Method designated to send content to Claude & Rupa's OOV service
        to extract eventual new words, terms and/or phrases and add them into
        Elasticsearch's 'ik_smart' analyzer's dictionairy files (.dic).
        """
        try:
            # 1. Send request with content to OOV service
            if text is not None:
                req = DataRequest(self._return_text, 'get',
                                  text, url=self.server)
            else:
                req = DataRequest(None, 'get', url=self.server)

            if req.response.ok:
                segments = set(req.response.json()["segmentresult"])
                es = LingtelliElastic()
                # 2. Send a similar request to Elasticsearch's /_analyze endpoint
                analyzer_segments = es.analyze(text)
                # 3. Compare results by figuring out which terms exist in OOV result
                #       that does not exist in the /_analyze results.
                results = segments - analyzer_segments
                # 4. Return the words, terms and/or phrases that are new.
                return results

            self.logger.msg = "Did not get an OK response from {}!".format(
                self.server)
            self.logger.error()
            raise self.logger

        except Exception as err:
            self.logger.msg = "Could not compare data from {} with Elasticsearch analyzer's!".format(
                self.server)
            self.logger.error(extra_msg=str(err), orgErr=err)
            raise self.logger from err

    def _save_results(self):
        """
        Method designated to add results from _run() into Elasticsearch's
        'ik_smart' analyzer's dictionairy files (.dic).
        """
        self.logger.msg = "Results from OOV service: ".format(self.results)
        self.logger.info(
            extra_msg="Number of new terms: {}".format(len(self.results)))

        if question_check("Do you wish to add these new terms, words and/or phrases to .dic files?"):
            content = None
            try:
                # 1. Open .dic file with content
                with open(DIC_FILE, 'r') as dic_file:
                    content = dic_file.readlines()

                # 2. Add content to the file
                if content is not None:
                    for item in self.results:
                        content.append(item)
                    content.sort()

                with open(DIC_FILE, 'w') as dic_file:
                    dic_file.writelines(content)

            except Exception as err:
                self.logger.msg = "Could not save new terms, words and/or phrases to .dic file!"
                self.logger.error(extra_msg=str(err), orgErr=err)
                raise self.logger from err

            else:
                self.logger.msg = "Saved words/terms/phrases to .dic file " + \
                    Fore.LIGHTGREEN_EX + "successfully" + Fore.RESET + "!"
                self.logger.info(extra_msg="Added terms: " + Fore.LIGHTGREEN_EX + "{}".format(
                    ", ".join(self.results)) + Fore.RESET)

        else:
            self.logger.msg = "Not adding the words/terms/phrases to .dic files!"
            self.logger.info(extra_msg="Not added: " + Fore.LIGHTRED_EX + "{}".format(
                ", ".join(self.results)) + Fore.RESET)


if __name__ == "__main__":
    oov = OOVService()
