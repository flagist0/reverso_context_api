import requests
from bs4 import BeautifulSoup

from reverso_context_api.misc import ReversoException

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
        if credentials:
            self._login(*credentials)

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

    def _login(self, email, password):
        login_url = "https://account.reverso.net/Account/Login"
        request_verification_token = self._get_request_validation_token(login_url)

        antiforgery_cookie = self.cookies.get("Reverso.Account.Antiforgery")
        if not antiforgery_cookie:
            raise ReversoException("Could not log in: cannot retrieve antiforgery cookie")

        self.post(
            login_url,
            params={"returnUrl": "https://context.reverso.net/"},
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
                "referer": login_url,
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "navigate",
                "sec-fetch-user": "?1",
                "sec-fetch-dest": "document",
                "X-Requested-With": None,
                "Accept-Encoding": None,
                "Connection": None,
                "Content-Length": None,
            })

    def _get_request_validation_token(self, login_url):
        r = self.get(
            login_url,
            params={
                "returnUrl": "https://context.reverso.net/",
                "lang": "en"
            })

        soup = BeautifulSoup(r.text, features="html.parser")
        token_tag = soup.find("input", attrs=dict(name="__RequestVerificationToken", type="hidden"))
        if token_tag is None:
            raise ReversoException("Cannot find __RequestVerificationToken in login page", soup=soup)
        return token_tag.attrs["value"]
