import requests
from bs4 import BeautifulSoup

from reverso_context_api.misc import ReversoException

LOGIN_URL = "https://account.reverso.net/Account/Login"
RETURN_URL = "https://context.reverso.net/translation/"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:77.0) Gecko/20100101 Firefox/77.0"
DEFAULT_TIMEOUT = 5

REQUEST_DEFAULT_HEADERS = {
    "Origin": "https://context.reverso.net",
    "Accept-Language": "en-US,en;q=0.5",
    "X-Requested-With": "XMLHttpRequest",
}


class ReversoSession(requests.Session):
    """Customize request params and response validation"""
    def __init__(self, credentials=None, user_agent=None):
        super().__init__()
        self.headers["User-Agent"] = user_agent or DEFAULT_USER_AGENT
        self.timeout = DEFAULT_TIMEOUT
        for header, val in REQUEST_DEFAULT_HEADERS.items():
            self.headers[header] = val

        self._credentials = credentials
        self.logged_in = False

    def request(self, method, url, **kwargs):
        r = super().request(method, url, **kwargs)
        r.raise_for_status()
        return r

    def json_request(self, method, url, data=None, **kwargs):
        r = self.request(method, url, json=data, **kwargs)

        contents = r.json()
        if "error" in contents:  # Reverso returns errors in body
            raise ReversoException(contents["error"], response=r)
        return r

    def login(self):
        if self._credentials is None:
            raise ReversoException("You have to set credentials to be able to log in")

        if self.logged_in:
            return

        request_verification_token = self._get_request_validation_token()

        antiforgery_cookie = self.cookies.get("Reverso.Account.Antiforgery")
        if not antiforgery_cookie:
            raise ReversoException("Could not log in: cannot retrieve antiforgery cookie")

        self._request_login(request_verification_token)
        self.logged_in = True

    def _request_login(self, request_verification_token):
        email, password = self._credentials
        r = self.post(
            LOGIN_URL,
            params={
                "returnUrl": RETURN_URL},
            data={
                "Email": email,
                "Password": password,
                "RememberMe": "true",
                "__RequestVerificationToken": request_verification_token
            },
            headers={
                "content-type": "application/x-www-form-urlencoded",
                "authority": "https://account.reverso.net",
                "origin": "https://account.reverso.net",
                "referer": LOGIN_URL,
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "navigate",
                "sec-fetch-user": "?1",
                "sec-fetch-dest": "document",
                "X-Requested-With": None,
                "Accept-Encoding": None,
                "Connection": None,
                "Content-Length": None,
            })
        if r.url != RETURN_URL:
            raise ReversoException("Could not login, please check your credentials")

    def _get_request_validation_token(self):
        r = self.get(
            LOGIN_URL,
            params={
                "returnUrl": RETURN_URL,
                "lang": "en"
            })

        soup = BeautifulSoup(r.text, features="html.parser")
        token_tag = soup.find("input", attrs=dict(name="__RequestVerificationToken", type="hidden"))
        if token_tag is None:
            raise ReversoException("Cannot find __RequestVerificationToken in login page", soup=soup)
        return token_tag.attrs["value"]
