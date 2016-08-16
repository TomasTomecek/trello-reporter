# -*- coding: utf-8 -*-
"""
notes:

 * trello_id -- we don't trust trello's ID system
"""

from __future__ import unicode_literals

import logging
import re

from trello_reporter.charting.harvesting import Harvestor

from dateutil import parser as dateparser
from dateutil.tz import tzutc

from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.postgres.fields import JSONField


logger = logging.getLogger(__name__)


class BoardQuerySet(models.QuerySet):
    pass


class BoardManager(models.Manager):
    def by_id(self, board_id):
        return self.get(id=board_id)

    def by_id_cached(self, board_id):
        return self.filter(id=board_id).prefetch_related("card_actions")[0]


class Board(models.Model):
    trello_id = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=255, null=True)

    objects = BoardManager.from_queryset(BoardQuerySet)()

    def __unicode__(self):
        return "%s (%s)" % (self.trello_id, self.name)

    @classmethod
    def list_boards(cls):
        """
        list boards for currently logged in user

        :return: boards query
        """
        boards = Harvestor.list_boards()  # FIXME: decouple
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
        Sprint.refresh(self)
        Sprint.set_completed_list(self)


class Card(models.Model):
    """
    trello card, doesn't make sense to store anything here since it changes in time, that's what
    we have actions for
    """
    trello_id = models.CharField(max_length=32)
    name = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    # due_dt = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return "%s (%s)" % (self.trello_id, self.name)

    @property
    def latest_action(self):
        try:
            return self.actions.latest()
        except IndexError:
            return None


class ListQuerySet(models.QuerySet):
    def for_board(self, board):
        return self.filter(card_actions__board=board)

    def name_matches_re(self, regex):
        return self.filter(name__iregex=regex)

    def name_is_in(self, f):
        return self.filter(name__in=f)

    def distinct_list(self):
        return self.distinct("card_actions__list")


class ListManager(models.Manager):
    def filter_lists_for_board(self, board, f=None, order_by=None):
        """
        filter lists for board

        :param board:
        :param f: list of str or None
        :param order_by: tuple of str or None
        """
        query = self.for_board(board)

        if f:
            logger.debug("limiting lists to %s", f)
            query = query.name_is_in(f)
        else:
            query = query.filter(name__isnull=False)
        if order_by:
            query = query.order_by(*order_by)
        query = query.distinct_list().prefetch_related("card_actions")
        return query

    def get_all_listnames_for_board(self, board):
        return list(self.filter_lists_for_board(board).values_list("name", flat=True))

    def lists_for_board_match_regex(self, board, regex):
        # distinct is important; it returns one entry per card action
        lists = self.for_board(board).name_matches_re(regex).distinct_list()
        return lists

    def sprint_archiving_lists_for_board(self, board):
        """ get lists which are used for archiving cards finished during a sprint """
        regex = r"^\s*sprint \d+( \(completed?\))?$"
        return self.lists_for_board_match_regex(board, regex)

    def completed_lists(self, board):
        """ there may be multiple completed lists which are being archived continuously """
        regex = r"^completed?$"
        return self.lists_for_board_match_regex(board, regex)


class List(models.Model):
    trello_id = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    objects = ListManager.from_queryset(ListQuerySet)()

    def __unicode__(self):
        return "%s (%s)" % (self.trello_id, self.name)

    @property
    def latest_action(self):
        return self.card_actions.latest()

    @property
    def latest_stat(self):
        return self.stats.latest()

    @property
    def story_points(self):
        return ListStat.objects.latest_stat_for_list(self).story_points_rt

    @classmethod
    def get_or_create_list(cls, trello_list_id, list_name):
        trello_list, _ = List.objects.get_or_create(trello_id=trello_list_id)
        if list_name is not None:
            # set or update the list name
            trello_list.name = list_name
        trello_list.save()
        return trello_list


class ListStatQuerySet(models.QuerySet):
    def for_board(self, board):
        return self.filter(card_action__board=board)

    def for_list(self, li):
        return self.filter(list=li)

    def for_lists(self, list_ids):
        return self.filter(list__id__in=list_ids)

    def for_list_names(self, list_names):
        return self.filter(list__name__in=list_names)

    def in_range(self, beginning, end):
        return self.filter(card_action__range=(beginning, end))

    def before(self, date):
        return self.filter(card_action__date__lt=date)

    def unique_list(self):
        """ don't duplicate lists """
        return self.order_by('list', '-card_action__date').distinct('list')


class ListStatManager(models.Manager):
    def latest_stat_for_list(self, li):
        return self.for_list(li).latest()

    def stats_for_lists_in_range(self, list_ids, beginning, end):
        return self \
            .for_lists(list_ids) \
            .in_range(beginning, end) \
            .select_related("list", "card_action")

    def stats_for_lists_before(self, board, list_names, before):
        return self \
           .for_board(board) \
           .for_list_names(list_names) \
           .before(before) \
           .unique_list()

    def sum_cards_for_lists_before(self, board, list_names, before):
        # NotImplementedError: aggregate() + distinct(fields) not implemented.
        return sum([x.cards_rt for x in self.stats_for_lists_before(
            board, list_names, before)])

    def sum_sp_for_lists_before(self, board, list_names, before):
        # NotImplementedError: aggregate() + distinct(fields) not implemented.
        return sum(filter(None, [x.story_points_rt for x in self.stats_for_lists_before(
            board, list_names, before)]))


class ListStat(models.Model):
    """
    statistics of lists: # number of cards present in a given time
    """
    # list which is affected by this ca: it's possible to list != card_action.list
    list = models.ForeignKey(List, models.CASCADE, related_name="stats")
    # there can be 2 stats for every action: -1 for previous list, +1 for next
    card_action = models.ForeignKey("CardAction", models.CASCADE, related_name="stats")
    diff = models.SmallIntegerField()
    # running total of cards count on a list
    cards_rt = models.IntegerField(blank=True, null=True)
    # running total of story points on a list
    story_points_rt = models.IntegerField(blank=True, null=True)

    objects = ListStatManager.from_queryset(ListStatQuerySet)()

    class Meta:
        get_latest_by = "card_action__date"

    def __unicode__(self):
        return "[c=%s sp=%s] %s (%s)" % (self.cards_rt, self.story_points_rt,
                                         self.diff, self.card_action)

    @classmethod
    def create_stat(cls, ca, list, diff, cards_rt, sp_rt):
        # TODO atomic
        o, created = cls.objects.get_or_create(
            card_action=ca,
            diff=diff,
            list=list,
        )
        if created:
            o.cards_rt = cards_rt
            o.story_points_rt = sp_rt
            o.save()
        else:
            logger.error("there is already stat for action %s", ca)
        return o


class CardActionQuerySet(models.QuerySet):
    def for_board(self, board):
        return self.filter(board=board)

    def for_list(self, li):
        return self.filter(list=li)

    def since(self, date):
        return self.filter(date__gte=date)

    def before(self, date):
        return self.filter(date__lte=date)

    def ordered_desc(self):
        return self.order_by("-date")


class CardActionManager(models.Manager):
    def get_card_actions_on_board_in(self, board, date=None):
        """ this is a time machine: shows board state in a given time """
        query = self \
            .for_board(board) \
            .order_by('card', '-date') \
            .distinct('card')
        if date:
            query = query.before(date)
        return query.select_related("list", "card", "board")

    def card_actions_on_list_names_in(self, board, list_names, date):
        cas = self.get_card_actions_on_board_in(board, date)
        return self.filter(id__in=[x.id for x in cas], list__name__in=list_names).select_related(
            "list", "card", "board"
        )

    def safe_card_actions_on_list_in(self, board, li, date=None):
        """ aggregate + distinct is not implemented """
        cas = self.get_card_actions_on_board_in(board, date=date)
        return self.filter(id__in=[x.id for x in cas], list=li)

    def story_points_on_list_in(self, board, li, date):
        return self.safe_card_actions_on_list_in(board, li, date) \
            .aggregate(models.Sum("story_points"))["story_points__sum"]

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
    story_points = models.IntegerField(null=True, default=0)

    previous_action = models.OneToOneField("self", related_name="next_action", null=True,
                                           blank=True)
    # when copying cards, this is the original card, not the newly created one
    card = models.ForeignKey(Card, models.CASCADE, related_name="actions")
    # present list
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

    def __unicode__(self):
        return "[%s] %s %s" % (self.action_type, self.card, self.date)

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
    def rename(self):
        try:
            self.data["data"]["old"]["name"]
        except KeyError:
            return False
        else:
            return True

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
        try:
            return self.data["data"]["card"]["name"]
        except KeyError:
            return None

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

    # FIXME: this needs to be atomic
    @classmethod
    def from_trello_response_list(cls, board, actions):
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

            if ca.card_name and card.name != ca.card_name:
                card.name = ca.card_name[:255]  # some users are just fun
                card.save()

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
                    # this should not happen, it means that trello returned something
                    # we didn't expect: let's start card history here; likely it got on the board
                    # from other board or is now on different board
                    logger.info("update card %s (%s): previous state is unknown",
                                ca.trello_card_id, ca.card_name)

                if ca.archiving:
                    ca.list = None
                    ca.is_archived = True
                elif ca.opening or ca.rename:
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
                    logger.info("card %s (%s) has unknown previous state",
                                ca.trello_card_id, ca.card_name)
                    # default card?
                    continue

            points_str = CardAction.get_story_points(ca.card_name)
            if points_str is not None:
                ca.story_points = int(points_str)
            ca.previous_action = previous_action
            ca.save()

            # ListStats
            if previous_action:
                diff = -1
                previous_list = previous_action.list
                if previous_list:
                    previous_list_stat = ListStat.objects.latest_stat_for_list(previous_list)
                    cards_rt = previous_list_stat.cards_rt
                    sp_rt = previous_list_stat.story_points_rt
                    ListStat.create_stat(ca, previous_list, diff, cards_rt + diff,
                                         sp_rt + (diff * ca.story_points))
            if ca.list:
                diff = 1
                try:
                    current_list_stat = ListStat.objects.latest_stat_for_list(ca.list)
                    cards_rt = current_list_stat.cards_rt
                    sp_rt = current_list_stat.story_points_rt
                except ObjectDoesNotExist:
                    cards_rt = 0
                    sp_rt = 0
                ListStat.create_stat(ca, ca.list, diff, cards_rt + diff,
                                     sp_rt + (diff * ca.story_points))

            # Sprints


class Sprint(models.Model):
    """

    """
    start_dt = models.DateTimeField(db_index=True, blank=True, null=True)
    end_dt = models.DateTimeField(db_index=True, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    sprint_number = models.IntegerField(db_index=True, blank=True, null=True)
    board = models.ForeignKey(Board, models.CASCADE, related_name="sprints")
    # list with completed cards for the sprint
    completed_list = models.OneToOneField(List, models.CASCADE, related_name="sprint",
                                          blank=True, null=True)
    due_card = models.OneToOneField(Card, models.CASCADE, related_name="sprint",
                                    blank=True, null=True)

    def __unicode__(self):
        return "[%s] %s → %s" % (self.sprint_number, self.start_dt, self.end_dt)

    @classmethod
    def refresh(cls, board):
        """
        calculate sprints based on "Sprint \d+" card
        :param board:
        :return:
        """
        # TODO (optimisation)
        # TODO incremental search
        regex = r"^\s*sprint \d+$"
        cards = CardAction.objects \
            .filter(board=board) \
            .filter(card__name__iregex=regex) \
            .order_by("card", "-date") \
            .distinct("card") \
            .values_list("card__trello_id", flat=True)

        due_dict = Harvestor.get_due_of_cards(cards)

        sprint_number_re = re.compile(r"(\d+)")

        for card_id, due in due_dict.items():
            sprint, created = cls.objects.get_or_create(board=board, end_dt=due)
            if created:
                first = CardAction.objects.filter(card__trello_id=card_id).earliest()
                last = CardAction.objects.filter(card__trello_id=card_id).latest()
                sprint.start_dt = first.date
                sprint.name = last.card_name
                sprint.due_card = last.card
                sprint.sprint_number = sprint_number_re.findall(last.card_name)[0]
                sprint.save()

    @classmethod
    def set_completed_list(cls, board):
        """
        find completed list and assign it to correct sprint
        """
        for sprint in Sprint.objects.filter(board=board, completed_list__isnull=True):
            regex = r"^\s*sprint %d" % sprint.sprint_number
            try:
                li = List.objects.filter(card_actions__board=board, name__iregex=regex).latest("card_actions__date")
            except ObjectDoesNotExist:
                logger.debug("it seems that sprint %s has not finished yet", sprint)
                continue
            sprint.completed_list = li
            logger.info("sprint %s cards are in list %s", sprint, li)
            sprint.save()
