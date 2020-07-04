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
        Language can be redefined for api calls
        :param source_lang: Default source language
        :param target_lang: Default target language
        :param credentials: Optional login and password
        :param user_agent: User agent string that will be used for API calls
        """
        self._source_lang, self._target_lang = source_lang, target_lang
        self._login, self._password = credentials
        self._session = ReversoSession(user_agent=user_agent)

    def get_suggestions(self, text, source_lang=None, target_lang=None, with_fuzzy=False):
        data = {
            "search": text,
            "source_lang": source_lang or self._source_lang,
            "target_lang": target_lang or self._target_lang
        }
        r = self._session.json_request("POST", BASE_URL + "bst-suggest-service", data)

        parts = ["suggestions"]
        if with_fuzzy:
            parts += ["fuzzy1", "fuzzy2"]

        contents = r.json()
        for part in parts:
            for term in contents[part]:
                suggestion = term["suggestion"]
                yield suggestion


if __name__ == "__main__":
    c = Client("de", "ru")
    for suggestion in c.get_suggestions("we"):
        print(suggestion)
