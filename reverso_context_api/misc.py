BASE_URL = "https://context.reverso.net/"


class ReversoException(Exception):
    def __init__(self, error, **context):
        super().__init__("Got error during communication with Reverso Context: {}".format(error))
        self.context = context


def drop_none(d):
    return {k: v for k, v in d.items() if v is not None}
