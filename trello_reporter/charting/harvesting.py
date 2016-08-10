"""
Module for fetching data from trello
"""

import logging
import os
import trello


# TODO: initiate user tokens, don't use mine!
client = trello.TrelloClient(
    api_key=os.environ["API_KEY"],
    api_secret=os.environ["API_SECRET"],
    token=os.environ["OAUTH_TOKEN"],
    token_secret=os.environ["OAUTH_SECRET"]
)

logger = logging.getLogger(__name__)


class Harvestor:

    @classmethod
    def get_card_actions(cls, board, since=None):
        """
        fetch card actions relevant to movement of cards on a specific board

        :param board: instance of trello_reporter.charting.models.Board
        :param since: datetime or None
        :return: list of json-like structures
        """
        logger.info("fetch card actions for board %s, since=%s", board, since)
        response = []
        before = None
        filters = [
            "createCard",
            "updateCard:idList",
            "updateCard:closed",
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
            j = client.fetch_json('/boards/' + board.trello_id + '/actions', query_params=f)
            if not j:
                # trello returns [] if there are no actions
                break
            before = j[-1]["date"]
            response += j
        response.reverse()  # oldest first
        return response

    @classmethod
    def list_boards(cls):
        boards = client.list_boards()
        return boards

# list_names = {
#     li["id"]: li["name"]
#     for li in client.fetch_json(
#         "/boards/" + board.id + "/lists",
#         query_params={"cards": "none", "filter": "all", "fields": "name"}
#     )
# }
# p(list_names)
# p(
#     client.fetch_json(
#         "/lists/56d06b5fdd3fed5b0b6381b5/actions",
#         query_params={"limit": 1000}
#     )
# )
