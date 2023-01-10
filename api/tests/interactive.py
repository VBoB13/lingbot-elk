# Module designated to include code for interactive tests for
# the Lingtelli ELK stack and its related servies.
from colorama import Fore

from es.elastic import LingtelliElastic
from errors.errors import TestError
from helpers.interactive import question_check
from params.definitions import SearchGPT, SearchField

es = LingtelliElastic()
logger = TestError(__file__, "tests.interactive.__main__")


def enter_values(separated: bool) -> SearchGPT:
    """
    Function for entering test values (for SearchGPT) object separately.
    """
    if separated:
        index = input("Which index would you like to test? Index: ")
        default_field = es.known_indices[index]["context"]
        search_term = input("What would you like to search for? Term: ")
        field = SearchField(name=default_field, search_term=search_term)
        return SearchGPT(vendor_id=index, match=field)
    else:
        answer = input(
            "Please enter the data in the following format: '<vendor_id>,<search_term>': ")
        answers = answer.split(",")
        index = answers[0]
        default_field = es.known_indices[index]["context"]
        search_term = answers[1]
        field = SearchField(name=default_field, search_term=search_term)
        return SearchGPT(vendor_id=index, match=field)


if __name__ == "__main__":
    more = True
    more = question_check("Test GPT3 session memory? (Y/N): ")
    all_answers = []
    while more:
        separately = question_check(
            "Want to enter the values separately? (Y/N): ")
        data = enter_values(separately)
        try:
            response = es.search_gpt(data)
        except Exception as err:
            logger.msg = "Could NOT test GPT service!"
            logger.error(extra_msg=str(err), orgErr=err)
            more = question_check("Try again? (Y/N): ")
            if more:
                continue
            break
        all_answers.append(response)
        # Ask if user wants to test more
        more = question_check("Want to do more tests? (Y/N): ")
    print_all = question_check("Print all results from all tests? (Y/N): ")
    if print_all:
        for num, answer in enumerate(all_answers):
            logger.msg = "Answer #%s: " % num+1 + Fore.LIGHTCYAN_EX + answer + Fore.RESET
            logger.info()
