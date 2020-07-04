import requests

BASE_URL = "https://context.reverso.net/"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:77.0) Gecko/20100101 Firefox/77.0"
DEFAULT_TIMEOUT = 5
REQUEST_DEFAULT_HEADERS = {
    "Origin": "https://context.reverso.net",
    "Accept-Language": "en-US,en;q=0.5",
    "X-Requested-With": "XMLHttpRequest",
}


class ReversoException(Exception):
    def __init__(self, error, **context):
        super().__init__("Got error during communication with Reverso Context: {}".format(error))
        self.context = context


class ReversoSession(requests.Session):
    """Customize request params and response validation"""
    def __init__(self, user_agent=None):
        super().__init__()
        self.headers["User-Agent"] = user_agent or DEFAULT_USER_AGENT
        self.timeout = DEFAULT_TIMEOUT
        for header, val in REQUEST_DEFAULT_HEADERS.items():
            self.headers[header] = val

    def request(self, method, url, **kwargs):
        r = super().request(method, url, **kwargs)
        r.raise_for_status()
        return r

    def json_request(self, method, url, data, **kwargs):
        r = self.request(method, url, json=data, **kwargs)

        contents = r.json()
        if "error" in contents:  # Reverso returns errors in body
            raise ReversoException(contents["error"], response=r)
        return r


class Client(object):
    def __init__(self, source_lang, target_lang, credentials=(None, None), user_agent=None):
        """
        Language can be redefined in api calls
        :param source_lang: Default source language
        :param target_lang: Default target language
        :param credentials: Optional login and password
        :param user_agent: User agent string that will be used for API calls
        """
        self._source_lang, self._target_lang = source_lang, target_lang
        self._login, self._password = credentials
        self._session = ReversoSession(user_agent=user_agent)

    def get_translations(self, text, source_lang=None, target_lang=None):
        """Yields found translations of word (without context)
        For example:
        >>> list(Client("de", "en").get_translations("braucht"))
        ['needed', 'required', 'need', 'takes', 'requires', 'take', 'necessary'...]
        """
        r = self._request_translations(text, source_lang, target_lang)

        content = r.json()
        for entry in content["dictionary_entry_list"]:
            yield entry["term"]

    def get_suggestions(self, text, source_lang=None, target_lang=None, fuzzy_search=False, cleanup=True):
        """
        Yields search suggestions for passed text
        For example:
        >>> list(Client("de", "en").get_suggestions("bew")))
        ['Bewertung', 'Bewegung', 'bewegen', 'bewegt', 'bewusst', 'bewirkt', 'bewertet'...]

        :param fuzzy_search: Allow fuzzy search (can find suggestions for words with typos: entzwickl -> Entwickler)
        :param cleanup: Remove <b>...</b> around requested part in each suggestion
        """
        r = self._request_suggestions(text, source_lang, target_lang)
        parts = ["suggestions"]
        if fuzzy_search:
            parts += ["fuzzy1", "fuzzy2"]

        contents = r.json()
        for part in parts:
            for term in contents[part]:
                suggestion = term["suggestion"]

                if cleanup:
                    suggestion = suggestion.replace("<b>", "").replace("</b>", "")

                yield suggestion

    def _request_translations(self, text, source_lang, target_lang, target_text=None, page_num=1):
        data = {
            "source_lang": source_lang or self._source_lang,
            "target_lang": target_lang or self._target_lang,
            "mode": 0,
            "npage": page_num,
            "source_text": text,
            "target_text": target_text or "",
        }
        r = self._session.json_request("POST", BASE_URL + "bst-query-service", data)
        return r

    def _request_suggestions(self, text, source_lang, target_lang):
        data = {
            "search": text,
            "source_lang": source_lang or self._source_lang,
            "target_lang": target_lang or self._target_lang
        }
        r = self._session.json_request("POST", BASE_URL + "bst-suggest-service", data)
        return r


if __name__ == "__main__":
    c = Client("de", "en")
    print(list(Client("de", "en").get_suggestions("entzwickl", fuzzy_search=True)))
