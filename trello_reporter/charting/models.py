"""
notes:

 * trello_id -- we don't trust trello's ID system


TODO:
 * last day is full of 0s
"""

from __future__ import unicode_literals

import logging
import datetime
import collections

from dateutil import parser as dateparser
from dateutil.tz import tzutc

import intervaltree

from django.db import models
from django.contrib.postgres.fields import JSONField

from trello_reporter.charting.harvesting import Harvestor

logger = logging.getLogger(__name__)


class ChartInterval(object):
    def __init__(self):
        self.it = intervaltree.IntervalTree()
        self.values = set()

    def add(self, begin, end, value):
        self.it.addi(begin, end, value)
        self.values.add(value)

    def __str__(self):
        return "%s %s" % (self.values, self.it)


class BoardManager(models.Manager):
    pass


class Board(models.Model):
    trello_id = models.CharField(max_length=32)
    name = models.CharField(max_length=255, null=True)

    objects = BoardManager()

    def __str__(self):
        return self.name

    @classmethod
    def list_boards(cls):
        boards = Harvestor.list_boards()
        for board in boards:
            b, c = Board.objects.get_or_create(trello_id=board.id)
            b.name = board.name
            b.save()
        return Board.objects.all()

    def ensure_actions(self):
        """
        ensure that card actions are loaded, if not, load them
        """
        # TODO: load latest actions
        if self.card_actions.exists():
            return
        actions = Harvestor.get_card_actions(self)
        for action in actions:
            CardAction.from_trello_response_json(action)

    def actions_for_interval(self, beginning, end):
        """
        get list of card actions in specific interval

        :param beginning: datetime
        :param end: datetime
        :return: query of card actions
        """
        self.ensure_actions()
        return self.card_actions.filter(date__range=(beginning, end)).order_by("date")

    def group_card_movements(self, beginning=None, end=None, time_span=None):
        """
        load all card actions during the interval and transform it into specific format

        :return: dict, list; list of list names in the interval
        {
          day: {
            list_name: #number_of_movements
            listname2: ...
          }
        }
        """
        now = datetime.datetime.now(tz=tzutc())
        if beginning is None:
            beginning = now - datetime.timedelta(days=30)
        if time_span is None:
            time_span = datetime.timedelta(days=1)
        if end is None:
            end = now

        response = collections.OrderedDict()

        interval = self.get_movements_interval(beginning, end)

        n = beginning
        while True:
            interval_data = {}  # data in one unit

            n2 = n + time_span
            values = interval.it.search(n, n2)

            for value in values:
                interval_data.setdefault(value.data, 0)
                interval_data[value.data] += 1

            response[n.date()] = interval_data

            n = n2
            if n > end:
                break
        return response, list(interval.values)

    def get_movements_interval(self, beginning, end):
        """
        initiate interval with all card movements within

        :param beginning: datetime
        :param end: datetime
        :return: instance of ChartInterval
        """
        # oldest first
        card_actions = self.actions_for_interval(beginning, end)

        logger.debug("# actions: %d" % len(card_actions))

        # state of cards on one specific board in a given time
        # card_id -> (date, list_name)
        time_machine = {}
        interval = ChartInterval()
        # this is a list of cards we failed to process and needs to be processed separately
        cards_to_babysit = set()

        def create_card(card_action):
            if card_action.trello_board_id != self.trello_id:
                logger.info("card %s was created on board %s",
                            card_action.trello_card_id, card_action.trello_board_id)
                return
            try:
                target_list_name = card_action.list_name
            except KeyError:
                logger.warning("create card %s: list name not found", card_action.trello_card_id)
                # trello, you're so much fun
                # this happens when card was created on a different board
                # we don't care about that, let's skip
                return
            time_machine[card_action.trello_card_id] = (card_action.date, target_list_name)

        def update_card(card_action):
            """
            possible actions:
             * move card to different list
             * close card
            """
            try:
                previous_action_date, previous_list_name = time_machine[card_action.trello_card_id]
            except KeyError:
                logger.warning("update card %s: time machine doesn't know it", card_action.trello_card_id)
                # this should not happen, it means that trello returned something we didn't expect
                # let's process the card separately then
                cards_to_babysit.add(card_action.trello_card_id)
                return

            if card_action.closing:
                # card is closed
                current_list_name = "Closed"
            elif card_action.opening:
                # card is opened again
                current_list_name = card_action.list_name
            else:
                current_list_name = card_action.target_list_name

            interval.add(previous_action_date, card_action.date, previous_list_name)

            time_machine[card_action.trello_card_id] = (card_action.date, current_list_name)

        def delete_card(card_action):
            try:
                previous_action_date, previous_list_name = time_machine[card_action.trello_card_id]
            except KeyError:
                logger.warning("delete card %s form board: time machine doesn't know it",
                               card_action.trello_card_id)
                # default card?
                return
            interval.add(previous_action_date, card_action.date, previous_list_name)
            del time_machine[card_action.trello_card_id]

        def move_card_from_board(card_action):
            try:
                previous_action_date, previous_list_name = time_machine[card_action.trello_card_id]
            except KeyError:
                logger.warning("move card %s form board: time machine doesn't know it",
                               card_action.trello_card_id)
                # default card?
                return
            interval.add(previous_action_date, card_action.date, previous_list_name)
            del time_machine[card_action.trello_card_id]  # we no longer care about the card, it's gone

        actions_map = {
            "createCard": create_card,
            "updateCard": update_card,
            "moveCardToBoard": create_card,
            "moveCardFromBoard": move_card_from_board,
            "deleteCard": delete_card,
            "convertToCardFromCheckItem": create_card,  # we don't care it's a convert
            "copyCard": create_card,
        }

        for card_action in card_actions:
            logger.debug("[%s] card %s at %s", card_action.action_type, card_action.trello_card_id,
                         card_action.date)
            fn = actions_map[card_action.action_type]
            if fn is not None:
                fn(card_action)
            else:
                logger.critical("IMPLEMENT!!!")

        # record rest of the interval
        for card_id, (date, list_name) in time_machine.items():
            interval.add(date, end, list_name)

        logger.debug(interval)

        return interval

    @classmethod
    def from_trello_response_json(cls, trello_response):
        card, _ = Card.objects.get_or_create(trello_id=trello_response["data"]["card"]["id"])
        card.save()
        board, _ = Board.objects.get_or_create(trello_id=trello_response["data"]["board"]["id"],
                                               name=trello_response["data"]["board"].get("name"))
        board.save()

        logger.debug(card)
        logger.debug(board)

        c = CardAction(
            trello_id=trello_response["id"],
            date=dateparser.parse(trello_response["date"], tzinfos=tzutc),
            action_type=trello_response["type"],
            data=trello_response,
            card=card,
            board=board
        )
        c.save()
        return c


class Card(models.Model):
    """
    trello card, doesn't make sense to store anything here since it changes in time, that's what
    we have actions for
    """
    trello_id = models.CharField(max_length=32)

    def __str__(self):
        return str(self.trello_id)


class CardAction(models.Model):
    trello_id = models.CharField(max_length=32, db_index=True)
    # datetime when the event happened
    date = models.DateTimeField(db_index=True)
    # type of actions displayed as string
    action_type = models.CharField(max_length=32)
    # when copying cards, this is the original card, not the newly created one
    card = models.ForeignKey(Card, models.CASCADE, related_name="actions")
    board = models.ForeignKey(Board, models.CASCADE, related_name="card_actions")

    # complete response from trello API
    #
    # [{u'data': {u'board': {u'id': u'5783a02a78cd8946ec84572a',
    #                        u'name': u'Trello Reports',
    #                        u'shortLink': u'S4m1yrfb'},
    #             u'card': {u'id': u'5783b90cea9ad4c54ce998ff',
    #                       u'idList': u'5784d533c273958ad9c1a895',
    #                       u'idShort': 19,
    #                       u'name': u'Control chart',
    #                       u'shortLink': u'wHX1jFVZ'},
    #             u'listAfter': {u'id': u'5784d533c273958ad9c1a895',
    #                            u'name': u'Blocked'},
    #             u'listBefore': {u'id': u'5783a02a78cd8946ec84572d',
    #                             u'name': u'Next'},
    #             u'old': {u'idList': u'5783a02a78cd8946ec84572d'}},
    #   u'date': u'2016-07-12T11:32:14.696Z',
    #   u'id': u'5784d53e6238494254e0c964',
    #   u'idMemberCreator': u'54647c122edb0742214c751c',
    #   u'memberCreator': {u'avatarHash': u'b7f6d38057d04b49609572f7fea7d203',
    #                      u'fullName': u'Tomas Tomecek',
    #                      u'id': u'54647c122edb0742214c751c',
    #                      u'initials': u'TT',
    #                      u'username': u'tomastomecek1'},
    #   u'type': u'updateCard'},
    data = JSONField()

    def __str__(self):
        return "%s %s %s" % (self.card, self.action_type, self.board)

    @property
    def trello_card_id(self):
        return self.card.trello_id

    @property
    def trello_board_id(self):
        return self.board.trello_id

    @property
    def list_name(self):
        return self.data["data"]["list"]["name"]

    @property
    def target_list_name(self):
        """ get target list name for movement actions """
        return self.data["data"]["listAfter"]["name"]

    @property
    def opening(self):
        """ does this action opens the card? """
        return self.data["data"].get("old", {}).get("closed", False)

    @property
    def closing(self):
        """ does this action closes the card? """
        return self.data["data"]["card"].get("closed", False)

    @classmethod
    def from_trello_response_json(cls, trello_response):
        card, _ = Card.objects.get_or_create(trello_id=trello_response["data"]["card"]["id"])
        card.save()
        board, _ = Board.objects.get_or_create(trello_id=trello_response["data"]["board"]["id"],
                                               name=trello_response["data"]["board"].get("name"))
        board.save()

        logger.debug(card)
        logger.debug(board)

        c = CardAction(
            trello_id=trello_response["id"],
            date=dateparser.parse(trello_response["date"], tzinfos=tzutc),
            action_type=trello_response["type"],
            data=trello_response,
            card=card,
            board=board
        )
        c.save()
        return c
