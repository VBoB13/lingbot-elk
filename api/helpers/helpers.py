"""
For helper functions that don't make sense in any other module,
they get put in this module.
"""

import json
import os
import re
import requests
import socket
from heapq import nlargest
from logging import Logger

from colorama import Fore
from nltk import FreqDist
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from jieba.analyse import extract_tags

from params.definitions import TemplateModel


logger = Logger(__file__)


def _reset_logger_name():
    logger.name = "helpers.helpers:"


try:
    from settings.settings import CLAUDES_SERVER, CLAUDES_PORT
except ImportError:
    logger.name += "IMPORT"
    logger.warning(Fore.LIGHTYELLOW_EX +
                   "Import for CLAUDES_SERVER and CLAUDES_PORT failed! Setting values manually." + Fore.RESET)
    CLAUDES_SERVER = "192.168.1.132"
    CLAUDES_PORT = 3002
    _reset_logger_name()


def get_language(content: str) -> str:
    """
    Returns a string (`'CH'` or `'EN'`).
    """
    global logger
    logger.name += "get_language()"

    language = {
        "CH": "Traditional Chinese (ZH-TW)",
        "EN": "English (EN)"
    }
    lang = "CH"
    if (len(re.findall(r'[\u4e00-\u9fff]', content)) / len(content)) < 0.5:
        lang = "EN"

    logger.info("Language: {}".format(language[lang]))

    _reset_logger_name()

    return lang


def get_local_ip(org_ip: str) -> str:
    """
    Returns the local IP if the parameter `org_ip`'s value is `0.0.0.0`.
    Otherwise, the original value of `org_ip` is returned.
    """
    global logger
    logger.name += "get_local_ip()"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect((org_ip, 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
        _reset_logger_name()
    return IP


def get_synonymns(words: list, category: str) -> list[list[str]]:
    """
    Function that takes a word in a list as parameter and spits out another list of comma-separated words that are each others' synonyms.
    Returns: `list['word1, syn1-1, syn1-2, syn1-3, ...', 'word2, syn2-1, syn2-2, syn2-3, ...', ...]`
    """
    global logger
    logger.name += "get_synonyms()"

    language = get_language(' '.join(words))
    lang_key = 'zh_' if language == "CH" else 'en_'

    acceptable_categories = ['travel', 'insurance', 'admin']
    final_results = []

    if category in acceptable_categories:
        try:
            data = {"word_list": words}
            # Take each word and send to synonym endpoint (Claude's service)
            response = requests.post(CLAUDES_SERVER + ":" +
                                     str(CLAUDES_PORT) + "/%s" % lang_key + "synonyms", data=json.dumps(data))
            if response.ok:
                data: dict[str, list[dict[str, str | list]]
                           ] = response.json()
                synonyms = data["synonym_list"]
                for word_obj in synonyms:
                    final_results.append(word_obj['syn_list'])

            return final_results

        except Exception as err:
            logger.msg = "Something went wrong when trying to get synonyms from Claude's service."
            logger.warning(extra=str(err))
            raise logger from err

        finally:
            _reset_logger_name()

    else:
        logger.error(
            "'category' parameter not acceptable! Must be one of %s" % str(
                acceptable_categories)
        )
        raise logger


def includes_chinese(text: str) -> bool:
    """
    Returns `True` if text has ANY Chinese characters within.
    """
    return len(re.findall(r'[\u4e00-\u9fff]', text)) >= 1


def summarize_text(text: str, language: str = "EN") -> str:
    """
    Takes a longer text as `str` and a `language` parameter as
    ['EN' | 'CH'] to summarize the text accordingly.
    """
    if language == "CH":
        num_sentences = 3
        num_keywords = 7
        keywords = extract_tags(text, topK=num_keywords, withWeight=True)

        sent_scores = {}
        for sentence in text.split("。"):
            score = 0
            for keyword, weight in keywords:
                if keyword in sentence:
                    score += weight
            sent_scores[sentence] = score

        summary_sentences = nlargest(
            num_sentences, sent_scores, key=sent_scores.get)
        summary = "。".join(summary_sentences)

        if len(summary) > 1500:
            summary = summary[:1500]

    elif language == "EN":
        sentences = sent_tokenize(text)
        words = word_tokenize(text)

        stop_words = set(stopwords.words('english'))
        filtered_words = [
            word for word in words if word.casefold() not in stop_words]

        word_freq = FreqDist(filtered_words)

        most_freq = nlargest(10, word_freq, key=word_freq.get)
        sent_scores = {}
        for sentence in sentences:
            for word in word_tokenize(sentence.lower()):
                if word in most_freq:
                    if len(sentence.split(' ')) < 30:
                        if sentence not in sent_scores.keys():
                            sent_scores[sentence] = word_freq[word]
                        else:
                            sent_scores[sentence] += word_freq[word]

        num_sentences = 5
        num_keywords = 7
        summary_sentences = nlargest(
            num_sentences, sent_scores, key=sent_scores.get)

        summary = ' '.join(summary_sentences)

    else:
        global logger
        logger.name += "summarize_text()"
        msg = "Cannot summarize text in any other language than these: English (EN), Traditional Chinese (ZH_TW)."
        logger.error(msg)

    return summary.replace('\n', '')


def validate_template_object(obj: TemplateModel) -> None:
    """
    Function that validates the values within object for setting custom templates for indices.
    """
    global logger
    logger.name += "validate_template_object"
    if len(obj.template) < 10 or len(obj.template) > 200:
        logger.msg = "Template either TOO long or TOO short!"
        logger.error(extra=f"\nLength: {len(obj.template)} ([< 10] OR  [> 200])")
        raise logger
    
    if obj.template and (not obj.sentiment or not obj.role):
        logger.msg = "If you want to implement a custom template, you need to provide" + \
            Fore.LIGHTRED_EX + " `sentiment`, `role`" + Fore.RESET + " paramteres!"
        logger.error(extra="\n`sentiment`: '%s'" %
                     str(obj.sentiment) + "\n`role`: '%s'" % str(obj.role))
        raise logger

    if len(obj.role) < 3 or len(obj.role) > 15:
        logger.msg = "The 'role' has to be >= 3 or <= 15 characters long!"
        logger.error(extra="Role length: %s" % str(len(obj.role)))
        raise logger

    if len(obj.sentiment) < 3 or len(obj.sentiment) > 50:
        logger.msg = "The 'sentiment' has to be >= 3 or <= 50 characters long!"
        logger.error(extra="Sentiment length: %s" %
                     str(len(obj.sentiment)))
        raise logger
    
    if "{role}" not in obj.template or\
            "{sentiment}" not in obj.template:
        logger.msg = "either '{role}' or '{sentiment}' CANNOT be found within said 'template'!"
        logger.error(extra="Template: " + obj.template)

    _reset_logger_name()
