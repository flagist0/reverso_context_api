import re
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


class _ReversoSession(requests.Session):
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
        Simple client for Reverso Context

        Language can be redefined in api calls
        :param source_lang: Default source language
        :param target_lang: Default target language
        :param credentials: Optional login and password
        :param user_agent: User agent string that will be used for API calls
        """
        self._source_lang, self._target_lang = source_lang, target_lang
        self._login, self._password = credentials
        self._session = _ReversoSession(user_agent=user_agent)

    def get_translations(self, text, source_lang=None, target_lang=None):
        """Yields found translations of word (without context)
        For example:
        >>> list(Client("de", "en").get_translations("braucht"))
        ['needed', 'required', 'need', 'takes', 'requires', 'take', 'necessary'...]
        """
        r = self._request_translations(text, source_lang, target_lang)

        contents = r.json()
        for entry in contents["dictionary_entry_list"]:
            yield entry["term"]

    def get_translation_samples(self, text, target_text=None, source_lang=None, target_lang=None, cleanup=True):
        """Yields pairs (source_text, translation) of context for passed text

        >>> import itertools  # just like other methods, this one returns iterator
        >>> c = Client("en", "de")
        >>> list(itertools.islice(c.get_translation_samples("cellar door", cleanup=False), 3)) # take first three samples
        [("And Dad still hasn't fixed the <em>cellar door</em>.",
          'Und Dad hat die <em>Kellertür</em> immer noch nicht repariert.'),
         ("Casey, I'm outside the <em>cellar door</em>.",
          'Casey, ich bin vor der <em>Kellertür</em>.'),
         ('The ridge walk and mountain bike trails are accessible from the <em>cellar door</em>.',
          'Der Ridge Walk und verschiedene Mountainbikestrecken sind von der <em>Weinkellerei</em> aus zugänglich.')]

        :param target_text: if there are many translations of passed text (see get_translations), with this parameter
                            you can narrow the sample search down to one passed translation
        :param cleanup: Remove <em>...</em> around requested part and its translation

        Based on example from get_translations: get first sample where 'braucht' was translated as 'required':
        >>> next(c.get_translation_samples("braucht", "required"))
        ('Für einen wirksamen Verbraucherschutz braucht man internationale Vorschriften.',
         'In order to achieve good consumer protection, international rules are required.')
        """
        for page in self._translations_pager(text, target_text, source_lang, target_lang):
            for entry in page["list"]:
                source_text, translation = entry["s_text"], entry["t_text"]
                if cleanup:
                    source_text = self._cleanup_html_tags(source_text)
                    translation = self._cleanup_html_tags(translation)
                yield source_text, translation

    def get_search_suggestions(self, text, source_lang=None, target_lang=None, fuzzy_search=False, cleanup=True):
        """
        Yields search suggestions for passed text

        >>> list(Client("de", "en").get_search_suggestions("bew")))
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
                    suggestion = self._cleanup_html_tags(suggestion)

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

    def _translations_pager(self, text, target_text=None, source_lang=None, target_lang=None):
        page_num, pages_total = 1, None
        while page_num != pages_total:
            r = self._request_translations(text, source_lang, target_lang, target_text, page_num=page_num)
            contents = r.json()
            pages_total = contents["npages"]
            yield contents
            page_num += 1

    @staticmethod
    def _cleanup_html_tags(text):
        """Remove html tags like <b>...</b> or <em>...</em> from text
        I'm well aware that generally it's a felony, but in this case tags cannot even overlap
        """
        html_tag_re = re.compile(r"<.*?>")
        text = re.sub(html_tag_re, "", text)
        return text
