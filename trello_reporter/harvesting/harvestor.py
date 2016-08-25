"""
Module for fetching data from trello

This is how a sample URL looks:

https://api.trello.com/1/cards/4eea503d91e31d174600008f?fields=name,idList&member_fields=fullName&key=[application_key]&token=[optional_auth_token]


"""

import urllib
import logging
import urlparse

import requests

from django.conf import settings


logger = logging.getLogger(__name__)


TRELLO_API_SCHEME = "https"
TRELLO_API_NETLOC = "api.trello.com"
API_VERSION = "1"


class Harvestor(object):

    def __init__(self, token, api_key=None):
        if api_key is None:
            api_key = settings.API_KEY
        self.token = token
        self.api_key = api_key
        self.params = {"token": token, "key": api_key}
        self.s = requests.Session()

    def url(self, endpoint, params=None):
        """
        construct absolute URL

        :param endpoint: str
        :param params: dict
        :return: str
        """
        params = params or {}
        params.update(self.params)
        encoded_params = urllib.urlencode(params)
        url = urlparse.urlunsplit(
            (TRELLO_API_SCHEME, TRELLO_API_NETLOC, API_VERSION + "/" + endpoint, encoded_params, "")
        )
        return url

    def get_json(self, url):
        response = self.s.get(url)
        if response.status_code == 401:
            logger.warning("can't access resource: %s", response.content)
            return
        return response.json()

    def get_card_actions(self, board_id, since=None):
        """
        fetch card actions relevant to movement and name changes of cards on a specific board

        :param board_id: str
        :param since: datetime or None
        :return: list of json-like structures
        """
        logger.info("fetch card actions for board %s, since=%s", board_id, since)
        response = []
        before = None
        filters = [
            "createCard",
            "updateCard:idList",
            "updateCard:closed",
            "updateCard:name",             # change story points, possibly
            "moveCardToBoard",
            "moveCardFromBoard",           # = delete card (?)
            "deleteCard",
            "convertToCardFromCheckItem",  # = create card
            "copyCard",                    # = create card
        ]
        filters_rendered = ",".join(filters)

        while True:
            f = {
                "filter": filters_rendered,
                "limit": 1000,  # "page" works only up to total 1k, we need to paginate by date
            }
            if before:
                f["before"] = before
            if since:
                f["since"] = since

            url = self.url('boards/' + board_id + '/actions', params=f)
            j = self.get_json(url)
            if not j:
                # trello returns [] if there are no actions
                break
            before = j[-1]["date"]
            response += j
        response.reverse()  # oldest first
        return response

    def list_boards(self):
        url = self.url('members/me/boards', params={"fields": "name"})
        return self.get_json(url)

    def get_due_of_cards(self, trello_card_ids):
        """

        :param trello_card_ids: list of str
        :return:
        """
        response = {}
        params = {"fields": "due"}
        for card_id in trello_card_ids:
            url = self.url("cards/" + card_id, params=params)
            j = self.get_json(url)
            if j:
                response[card_id] = j["due"]
        return response

    def get_token_info(self, token):
        url = self.url("tokens/" + token)
        return self.get_json(url)

    def get_member_info_by_token(self, token):
        url = self.url("tokens/" + token + "/member")
        return self.get_json(url)
