import urlparse

from .harvestor import Harvestor, API_VERSION, TRELLO_API_NETLOC, TRELLO_API_SCHEME


def test_url_composing():
    token = "123"
    api_key = "456"
    endpoint = "asdqwe"
    h = Harvestor(token, api_key=api_key)
    url = h.url(endpoint)
    split = urlparse.urlsplit(url)
    assert split[0] == TRELLO_API_SCHEME
    assert split[1] == TRELLO_API_NETLOC
    assert split[2] == "/" + API_VERSION + "/" + endpoint
    assert urlparse.parse_qs(split[3]) == {"token": [token], "key": [api_key]}
