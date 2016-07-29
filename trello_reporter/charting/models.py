"""
notes:

 * trello_id -- we don't trust trello's ID system
"""

from __future__ import unicode_literals

import logging
import datetime
import collections
import re

from dateutil import parser as dateparser
from dateutil.tz import tzutc

from trello_reporter.charting.harvesting import Harvestor

from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.postgres.fields import JSONField


logger = logging.getLogger(__name__)


class BoardManager(models.Manager):
    def get_by_id(self, board_id):
        return self.get(id=board_id)
        return self.filter(id=board_id).prefetch_related("card_actions")[0]


class Board(models.Model):
    trello_id = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=255, null=True)

    objects = BoardManager()

    def __str__(self):
        return self.name

    @classmethod
    def list_boards(cls):
        """
        list boards for currently logged in user

        :return: boards query
        """
        boards = Harvestor.list_boards()
        for board in boards:
            b, c = Board.objects.get_or_create(trello_id=board.id)
            b.name = board.name
            b.save()
        return Board.objects.all()

    def ensure_actions(self):
        """
        ensure that card actions were fetched and loaded inside database; if not, load them
        """
        try:
            latest_action = self.card_actions.latest()
        except ObjectDoesNotExist:
            logger.info("fetching all card actions")
            actions = Harvestor.get_card_actions(self)
        else:
            logger.info("fetching card actions since %s", latest_action.date)
            actions = Harvestor.get_card_actions(self, since=latest_action.date)

        CardAction.from_trello_response_list(self, actions)

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
        # TODO: add option to show/hide card archivals
        now = datetime.datetime.now(tz=tzutc())
        if beginning is None:
            beginning = now - datetime.timedelta(days=30)
        if time_span is None:
            time_span = datetime.timedelta(days=1)
        if end is None:
            end = now

        response = collections.OrderedDict()

        # TODO: do this async
        self.ensure_actions()

        lists = set()

        n = beginning
        while True:
            n2 = n + time_span

            list_stats = CardAction.objects.get_cards_per_list(self.id, n)
            lists.update(list_stats.keys())
            response[n.date()] = list_stats

            n = n2
            if n > end:
                break
        return response, list(lists)  # this is converted to list b/c set can't be json-serialized


class Card(models.Model):
    """
    trello card, doesn't make sense to store anything here since it changes in time, that's what
    we have actions for
    """
    trello_id = models.CharField(max_length=32)

    def __str__(self):
        return str(self.trello_id)

    @property
    def latest_action(self):
        try:
            return self.actions.first()
        except IndexError:
            return None


class List(models.Model):
    trello_id = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return "List(trello_id=%s, name=\"%s\")" % (self.trello_id, self.name)

    @classmethod
    def get_or_create_list(cls, trello_list_id, list_name):
        trello_list, _ = List.objects.get_or_create(trello_id=trello_list_id)
        if list_name is not None:
            # set or update the list name
            trello_list.name = list_name
        trello_list.save()
        return trello_list


class CardActionQuerySet(models.QuerySet):
    def for_board(self, board_id):
        return self.filter(board__id=board_id)

    def since(self, date):
        return self.filter(date__gte=date)

    def before(self, date):
        return self.filter(date__lte=date)

    def ordered_desc(self):
        return self.order_by("-date")


class CardActionManager(models.Manager):
    def get_cards_at(self, board_id, date):
        """ this is a time machine: shows board state in a given time """
        return self \
            .for_board(board_id) \
            .before(date) \
            .order_by('card', '-date') \
            .distinct('card') \
            .select_related("list", "card", "board")

    def get_cards_per_list(self, board_id, date):
        # list_name -> # of cards
        response = {}
        # FIXME how to do this with SQL?
        #   NotImplementedError: annotate() + distinct(fields) is not implemented.
        #  on the other hand this could work:
        #   .annotate(max_date=Max('student__score__date')).filter(date=F('max_date'))
        #  but we would have to query cards, not CAs
        for ca in self.get_cards_at(board_id, date):
            if ca.is_deleted or ca.is_archived:
                continue
            response.setdefault(ca.list.name, 0)
            response[ca.list.name] += 1
        return response

    def actions_for_board(self, board_id):
        return self.for_board(board_id) \
            .ordered_desc() \
            .select_related("list", "board", "card") \
            .prefetch_related(models.Prefetch("card__actions"))


class CardAction(models.Model):
    trello_id = models.CharField(max_length=32, db_index=True)
    # datetime when the event happened
    date = models.DateTimeField(db_index=True)
    # type of actions displayed as string
    action_type = models.CharField(max_length=32)
    story_points = models.IntegerField(null=True, blank=True)

    # when copying cards, this is the original card, not the newly created one
    card = models.ForeignKey(Card, models.CASCADE, related_name="actions")
    list = models.ForeignKey(List, models.CASCADE, default=None, null=True, blank=True,
                             related_name="card_actions")
    board = models.ForeignKey(Board, models.CASCADE, related_name="card_actions")
    
    is_archived = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

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

    objects = CardActionManager.from_queryset(CardActionQuerySet)()

    class Meta:
        get_latest_by = "date"
        ordering = ["-date", ]

    def __unicode__(self):
        return "[%s] %s (%s) %s" % (self.action_type, self.card, self.card_name, self.date)

    @property
    def trello_card_id(self):
        return self.card.trello_id

    @property
    def trello_list_id(self):
        return self.list.trello_id

    @property
    def trello_board_id(self):
        return self.board.trello_id

    @property
    def list_id_and_name(self):
        d = self.data["data"].get("list", {})
        return d.get("id", None), d.get("name", None)

    @property
    def list_name(self):
        return self.data["data"]["list"]["name"]

    @property
    def source_list_name(self):
        """ get source list name for movement actions """
        return self.data["data"]["listBefore"]["name"]

    @property
    def source_list_id(self):
        """ get source list name for movement actions """
        return self.data["data"]["listBefore"]["id"]

    @property
    def target_list_id_and_name(self):
        d = self.data["data"].get("listAfter", {})
        return d.get("id", None), d.get("name", None)

    @property
    def target_list_name(self):
        """ get target list name for movement actions """
        return self.data["data"]["listAfter"]["name"]

    @property
    def opening(self):
        """ does this action opens (sends to board) the card? """
        try:
            return self.data["data"]["old"]["closed"]
        except KeyError:
            return False

    @property
    def archiving(self):
        """ does this action closes (archives) the card? """
        try:
            was_closed = self.data["data"]["old"]["closed"]
        except KeyError:
            was_closed = True
        try:
            is_closed = self.data["data"]["card"]["closed"]
        except KeyError:
            is_closed = False
        return is_closed or not was_closed

    @property
    def card_name(self):
        return self.data["data"]["card"]["name"]

    @classmethod
    def get_story_points(cls, card_name):
        """

        :param card_name:
        :return:
        """
        regex = r"^\s*\((\d+)\)"
        try:
            return re.findall(regex, card_name)[0]
        except IndexError:
            return None

    @classmethod
    def from_trello_response_list(cls, board, actions):
        cards_to_babysit = []
        logger.debug("processing %d actions", len(actions))
        for action_data in actions:
            card, _ = Card.objects.get_or_create(trello_id=action_data["data"]["card"]["id"])
            card.save()

            ca = CardAction(
                trello_id=action_data["id"],
                date=dateparser.parse(action_data["date"], tzinfos=tzutc),
                action_type=action_data["type"],
                data=action_data,
                card=card,
                board=board
            )

            previous_action = card.latest_action

            # figure out list_name, archivals, removals and unicorns
            if ca.action_type in ["createCard", "moveCardToBoard",
                                  "copyCard", "convertToCardFromCheckItem"]:  # create-like events
                if ca.trello_board_id != board.trello_id:
                    logger.info("card %s was created on board %s",
                                ca.trello_card_id, ca.trello_board_id)
                    # we don't care about such state
                    continue
                # when list is changed (or on different board), name is missing; fun stuff!
                trello_list_id, list_name = ca.list_id_and_name
                ca.list = List.get_or_create_list(trello_list_id, list_name)

            elif ca.action_type in ["updateCard"]:  # update = change list, close or open
                if not previous_action:
                    logger.warning("update card %s: previous state is unknown",
                                   ca.trello_card_id)
                    # this should not happen, it means that trello returned something
                    # we didn't expect, let's process the card separately then
                    # FIXME: alternatively, we could start action history here
                    cards_to_babysit.append(ca)
                    continue

                if ca.archiving:
                    ca.list = None
                    ca.is_archived = True
                elif ca.opening:
                    # card is opened again
                    trello_list_id, list_name = ca.list_id_and_name
                    ca.list = List.get_or_create_list(trello_list_id, list_name)
                else:
                    trello_list_id, list_name = ca.target_list_id_and_name
                    ca.list = List.get_or_create_list(trello_list_id, list_name)

            elif ca.action_type in ["moveCardFromBoard", "deleteCard"]:  # delete
                if previous_action:
                    ca.list = None
                    ca.is_deleted = True
                else:
                    logger.warning("card %s has unknown previous state",
                                   ca.trello_card_id)
                    # default card?
                    continue

            points_str = CardAction.get_story_points(ca.card_name)
            if points_str is not None:
                ca.story_points = int(points_str)
            ca.save()

        # TODO
        logger.warning("you should process now these cards: %s", cards_to_babysit)
