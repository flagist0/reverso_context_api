import re

from reverso_context_api.misc import BASE_URL
from reverso_context_api.session import ReversoSession

FAVORITES_PAGE_SIZE = 50


class Client(object):
    def __init__(self, source_lang, target_lang, credentials=None, user_agent=None):
        """
        Simple client for Reverso Context

        Language can be redefined in api calls
        :param source_lang: Default source language
        :param target_lang: Default target language
        :param credentials: Optional login information: pair of (email, password)
        :param user_agent: Optional user agent string that will be used during API calls
        """
        self._source_lang, self._target_lang = source_lang, target_lang
        self._session = ReversoSession(credentials=credentials, user_agent=user_agent)

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

    def get_favorites(self, source_lang=None, target_lang=None, cleanup=True):
        """
        Yields context samples saved by you as favorites (you have to provide login credentials to Client to use it)
        :param source_lang: string of lang abbreviations separated by comma
        :param target_lang: same as source_lang
        :param cleanup: remove <em>...</em> tags marking occurance of source_text
        :return: dict of sample attrs (source/target lang/context/text)
        """
        for page in self._favorites_pager(source_lang, target_lang):
            for entry in page["results"]:
                yield self._process_fav_entry(entry, cleanup)

    def get_search_suggestions(self, text, source_lang=None, target_lang=None, fuzzy_search=False, cleanup=True):
        """
        Yields search suggestions for passed text

        >>> list(Client("de", "en").get_search_suggestions("bew"))
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

    def _translations_pager(self, text, target_text=None, source_lang=None, target_lang=None):
        page_num, pages_total = 1, None
        while page_num != pages_total:
            r = self._request_translations(text, source_lang, target_lang, target_text, page_num=page_num)
            contents = r.json()
            pages_total = contents["npages"]
            yield contents
            page_num += 1

    def _favorites_pager(self, source_lang=None, target_lang=None):
        source_lang = source_lang or self._source_lang
        target_lang = target_lang or self._target_lang

        self._session.login()

        start, total = 0, None
        while True:
            r = self._request_favorites(source_lang, target_lang, start)
            contents = r.json()
            total = contents["numTotalResults"]
            yield contents
            start += FAVORITES_PAGE_SIZE
            if start >= total:
                break

    def _request_translations(self, text, source_lang, target_lang, target_text=None, page_num=None):
        # defaults are set here because this method can be called both directly and via pager
        target_text = target_text or ""
        page_num = page_num or 1

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

    def _request_favorites(self, source_lang, target_lang, start):
        params = {
            "sourceLang": source_lang,
            "targetLang": target_lang,
            "start": start,
            "length": FAVORITES_PAGE_SIZE,
            "order": 10  # don't know yet what this value means, but it works
        }
        r = self._session.json_request("GET", BASE_URL + "bst-web-user/user/favourites", params=params)
        return r

    def _request_suggestions(self, text, source_lang, target_lang):
        data = {
            "search": text,
            "source_lang": source_lang or self._source_lang,
            "target_lang": target_lang or self._target_lang
        }
        r = self._session.json_request("POST", BASE_URL + "bst-suggest-service", data)
        return r

    def _process_fav_entry(self, entry, cleanup):
        entry_fields_map = {
            "srcLang": "source_lang",
            "srcText": "source_text",
            "srcContext": "source_context",
            "trgLang": "target_lang",
            "trgText": "target_text",
            "trgContext": "target_context"
        }
        fields_to_clean = {"srcContext", "trgContext"}

        processed_entry = {}
        for field_from, field_to in entry_fields_map.items():
            val = entry[field_from]
            if cleanup and field_from in fields_to_clean:
                val = self._cleanup_html_tags(val)
            processed_entry[field_to] = val
        return processed_entry

    @staticmethod
    def _cleanup_html_tags(text):
        """Remove html tags like <b>...</b> or <em>...</em> from text
        I'm well aware that generally it's a felony, but in this case tags cannot even overlap
        """
        return re.sub(r"<.*?>", "", text)
