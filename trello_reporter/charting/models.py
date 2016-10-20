# -*- coding: utf-8 -*-
"""
notes:

 * trello_id -- we don't trust trello's ID system
"""

from __future__ import unicode_literals

import logging
import re

from django.dispatch.dispatcher import receiver
from django.utils.dateparse import parse_datetime

from trello_reporter.charting.constants import SPRINT_CARDS_ACTIVE
from .constants import DATETIME_FORMAT
from trello_reporter.authentication.models import TrelloUser, KeyVal
from trello_reporter.harvesting.harvestor import Harvestor
from trello_reporter.harvesting.models import CardActionEvent

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.utils import DatabaseError
from django.db.models.signals import post_save
from django.utils import timezone


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
        return "%s (%s)" % (self.id, self.name)

    @classmethod
    def list_boards(cls, user, token):
        """
        list boards for currently logged in user

        :return: boards query
        """
        response = []
        # FIXME: decouple
        boards_json = Harvestor(token).list_boards()
        for board_json in boards_json:
            board = cls.get_or_create_board(board_json["id"], name=board_json["name"])
            BoardUserMapping.get_or_create(board, user)
            response.append(board)
        return response

    @classmethod
    def get_or_create_board(cls, trello_id, name=None):
        obj, created = cls.objects.get_or_create(trello_id=trello_id)
        if name and obj.name != name:
            obj.name = name
        obj.save()
        return obj

    def ensure_actions(self, token):
        """
        ensure that card actions were fetched and loaded inside database; if not, load them
        """
        h = Harvestor(token)
        try:
            latest_action = self.card_actions.latest()
        except ObjectDoesNotExist:
            logger.info("fetching all card actions")
            actions = h.get_card_actions(self.trello_id)
            initial_cards = h.get_cards_on_board(self.trello_id, actions[0]["date"])
            # these are synthetic events
            for c in sorted(initial_cards, key=lambda x: x["dateLastActivity"], reverse=True):
                actions.insert(0, {
                    "date": c["dateLastActivity"],
                    "type": "defaultCard",
                    "data": {
                        "board": {
                            "id": c["idBoard"]
                        },
                        "card": {
                            "id": c["id"],
                            "name": c["name"],
                        },
                        "list": {
                            "id": c["idList"]
                        }
                    }
                })
        else:
            logger.info("fetching card actions since %s", latest_action.date)
            actions = h.get_card_actions(self.trello_id, since=latest_action.date)

        CardAction.from_trello_response_list(self, actions)
        Sprint.refresh(self, token)
        Sprint.set_completed_list(self)


class BoardUserMapping(models.Model):
    """ M:N mapping between users and boards """
    board = models.ForeignKey(Board, models.CASCADE)
    user = models.ForeignKey(TrelloUser, models.CASCADE)

    def __unicode__(self):
        return "%s <-> %s" % (self.board, self.user)

    @classmethod
    def get_or_create(cls, board, user):
        obj, created = cls.objects.get_or_create(board=board, user=user)
        if created:
            obj.save()
        return obj


# This is my go on trying doing a raw postgresql sql query to get sprint cards with prefetched
# card actions with all the related tables; did not succeed
#
#     # "charting_cardaction"."id", "charting_cardaction"."trello_id",
#     #     "charting_cardaction"."date", "charting_cardaction"."action_type",
#     #     "charting_cardaction"."story_points", "charting_cardaction"."card_id",
#     #     "charting_cardaction"."list_id", "charting_cardaction"."board_id",
#     #     "charting_cardaction"."is_archived", "charting_cardaction"."is_deleted",
#     #     "charting_cardaction"."event_id", "charting_list"."id", "charting_list"."trello_id",
#     #     "charting_list"."name", "charting_board"."id", "charting_board"."trello_id",
#     #     "charting_board"."name", "harvesting_cardactionevent"."id",
#     #     "harvesting_cardactionevent"."data", "harvesting_cardactionevent"."processed_well"
#     #    INNER JOIN "charting_list" ON ("charting_cardaction"."list_id" = "charting_list"."id")
#     #    INNER JOIN "charting_board" ON ("charting_cardaction"."board_id" = "charting_board"."id")
#     #    INNER JOIN "harvesting_cardactionevent" ON ("charting_cardaction"."event_id" =
#                                                      "harvesting_cardactionevent"."id")
#     CARDS_WITH_LATEST = """\
# SELECT *
# FROM "charting_card"
# INNER JOIN (
#     SELECT "charting_cardaction"."id" AS card_action_id,
#            "charting_cardaction"."card_id" AS card_id
#     FROM "charting_cardaction"
#     ORDER BY "charting_cardaction"."date" DESC
# ) AS q ON ("charting_card"."id" = "card_id")
# INNER JOIN "charting_sprint_cards" ON ("charting_card"."id" = "charting_sprint_cards"."card_id")
# WHERE "charting_sprint_cards"."sprint_id" = %s
# """
class CardQuerySet(models.QuerySet):
    def for_sprint(self, sprint):
        return self.filter(sprints=sprint)


class CardManager(models.Manager):
    def sprint_cards(self, sprint):
        return self.for_sprint(sprint)

    def sprint_cards_with_latest_actions(self, sprint):
        cards = self.for_sprint(sprint)
        card_ids = [c.id for c in cards]

        cas = CardAction.objects.card_actions_for_cards(card_ids)
        idx = {}
        for ca in cas:
            idx[ca.card_id] = ca

        for card in cards:
            setattr(card, "latest_action", idx[card.id])

        return cards


class Card(models.Model):
    """
    trello card, doesn't make sense to store anything here since it changes in time, that's what
    we have actions for
    """
    trello_id = models.CharField(max_length=32)
    # this is the most up to date card name
    name = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    # due_dt = models.DateTimeField(blank=True, null=True)

    objects = CardManager.from_queryset(CardQuerySet)()

    def __unicode__(self):
        return "%s (%s)" % (self.id, self.name)


class ListQuerySet(models.QuerySet):
    def for_board(self, board):
        return self.filter(card_actions__board=board)

    def name_matches_re(self, regex):
        return self.filter(name__iregex=regex)

    def name_is_in(self, f):
        return self.filter(name__in=f)

    def distinct_list(self):
        return self.distinct("card_actions__list__name")

    def latest_lists(self):
        return self.order_by("card_actions__list__name", "-card_actions__date").distinct_list()


class ListManager(models.Manager):
    def filter_lists_for_board(self, board, f=None):
        """
        filter lists for board

        :param board:
        :param f: list of str or None
        """
        query = self.for_board(board).latest_lists()

        if f:
            logger.debug("limiting lists to %s", f)
            query = query.name_is_in(f)
        else:
            query = query.filter(name__isnull=False)
        return query

    def get_all_listnames_for_board(self, board):
        return sorted(set(self.filter_lists_for_board(board).values_list("name", flat=True)))

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
        return "%s (%s)" % (self.id, self.name)

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
        """ latest stat for lists """
        return self.filter(list__name__in=list_names)

    def in_range(self, beginning, end):
        return self.filter(card_action__date__range=(beginning, end))

    def before(self, date):
        return self.filter(card_action__date__lt=date)

    def unique_card(self):
        return self.order_by('card_action__card', '-card_action__date').distinct('card_action__card')

    def unique_list(self):
        """ don't duplicate lists """
        # here we care about list names, not list instances
        return self.order_by('list__name', '-card_action__date').distinct('list__name')


class ListStatManager(models.Manager):
    def latest_stat_for_list(self, li):
        return self.for_list(li).latest()

    def for_list_order_by_date(self, li):
        return self.for_list(li).order_by("-card_action__date").select_related(
            "card_action", "card_action__card")

    def for_list_in_range(self, li, beginning, end):
        return self.for_list_order_by_date(li).in_range(beginning, end).select_related(
            "card_action", "card_action__card", "card_action__event")

    def stats_for_lists_in_range(self, list_ids, beginning, end):
        return self \
            .for_lists(list_ids) \
            .in_range(beginning, end) \
            .select_related("list", "card_action")

    def stats_for_list_names_in_range(self, board, list_names, beginning, end):
        q = self \
            .for_board(board) \
            .for_list_names(list_names) \
            .in_range(beginning, end) \
            .select_related("list", "card_action")
        return q

    def stats_for_list_names_before(self, board, list_names, before):
        return self \
           .for_board(board) \
           .for_list_names(list_names) \
           .before(before) \
           .unique_list()

    def sum_cards_for_list_names_before(self, board, list_names, before):
        # NotImplementedError: aggregate() + distinct(fields) not implemented.
        return sum([x.cards_rt for x in self.stats_for_list_names_before(
            board, list_names, before)])

    def sum_sp_for_list_names_before(self, board, list_names, before):
        """ if you want to aggregate from multiple lists, e.g. in progress + next """
        # NotImplementedError: aggregate() + distinct(fields) not implemented.
        stats = self.stats_for_list_names_before(board, list_names, before)
        return sum(filter(None, [x.story_points_rt for x in stats]))

    def latest_sp_for_list_names_before(self, board, list_names, before):
        """
        # of story points on a list in a given time - specified as a array of names - it works
        for duplicate lists, don't use for aggregation!
        """
        return self.stats_for_list_names_before(board, list_names, before)[0].story_points_rt


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
        return "[c=%s sp=%s %s] %s (%s)" % (
            self.cards_rt, self.story_points_rt, self.list, self.diff, self.card_action)

    @classmethod
    def create_stat(cls, ca, list, diff, cards_rt, sp_rt):
        with transaction.atomic():
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

    def for_trello_card_id(self, trello_card_id):
        return self.filter(card__trello_id=trello_card_id)

    def for_list(self, li):
        return self.filter(list=li)

    def for_card(self, card):
        return self.filter(card=card)

    def for_cards(self, card_ids):
        return self.filter(card_id__in=card_ids)

    def for_list_names(self, list_names):
        return self.filter(list__name__in=list_names)

    def since(self, date):
        return self.filter(date__gte=date)

    def before(self, date):
        return self.filter(date__lte=date)

    def in_range(self, beginning, end):
        return self.filter(date__range=(beginning, end))

    def ordered_desc(self):
        return self.order_by("-date")

    def distinct_cards(self):
        return self.order_by('card', '-date').distinct('card')


class CardActionManager(models.Manager):
    def get_card_actions_on_board_in(self, board, date=None):
        """ this is a time machine: shows board state in a given time """
        query = self.for_board(board).distinct_cards()
        if date:
            query = query.before(date)
        return query.select_related("list", "card", "board", "event")

    def actions_on_board_in_range(self, board, beginning, end):
        """ this is a time machine: shows board state in a given time """
        query = self \
            .for_board(board) \
            .in_range(beginning, end)
        return query.select_related("list", "card", "board", "event")

    def card_actions_on_list_names_in(self, board, list_names, date=None):
        cas = self.get_card_actions_on_board_in(board, date=date)
        return self.filter(id__in=[x.id for x in cas], list__name__in=list_names).select_related(
            "list", "card", "board", "event"
        )

    def card_actions_for_cards(self, card_ids):
        cas = self.for_cards(card_ids).distinct_cards().select_related(
            "list", "card", "board", "event"
        )
        return cas

    def card_actions_on_list_names_in_range(self, board, list_names, beginning, end):
        cas = self.get_card_actions_on_board_in(board, end)
        return self \
            .since(beginning) \
            .for_list_names(list_names) \
            .filter(id__in=[x.id for x in cas]) \
            .select_related("list", "card", "board", "event")

    def card_actions_on_list_names_in_interval(self, board, list_names, beginning, end):
        cas = self.actions_on_board_in_range(board, beginning, end)
        return cas.for_list_names(list_names)

    def card_actions_on_list_names_in_interval_order_desc(self, board, list_names, beginning, end):
        return self.card_actions_on_list_names_in_interval(board, list_names, beginning, end) \
            .order_by("-date")

    def safe_card_actions_on_list_in(self, board, li, date=None):
        """ aggregate + distinct is not implemented """
        cas = self.get_card_actions_on_board_in(board, date=date)
        return self.filter(id__in=[x.id for x in cas], list=li).select_related("card", "board",
                                                                               "event", "list")

    def story_points_on_list_in(self, board, li, date):
        return self.safe_card_actions_on_list_in(board, li, date) \
            .aggregate(models.Sum("story_points"))["story_points__sum"]

    def actions_for_board(self, board):
        return self.for_board(board) \
            .ordered_desc() \
            .select_related("list", "board", "card") \
            .prefetch_related(models.Prefetch("card__actions"))

    def for_trello_card_id_on_list_names(self, trello_card_id, list_names):
        return self.for_trello_card_id(trello_card_id).for_list_names(list_names)

    def get_sprint_trello_card_ids(self, board):
        """ return a set of trello card ids which match regex for sprint cards """
        regex = r"^\s*sprint\D+\d+$"
        query = CardAction.objects \
            .filter(board=board) \
            .filter(card__name__iregex=regex) \
            .values_list("card__trello_id", flat=True)
        card_ids = set(query)
        return card_ids

    def latest_for_card(self, card):
        try:
            return self.for_card(card).latest()
        except ObjectDoesNotExist:
            return None


class CardAction(models.Model):
    trello_id = models.CharField(max_length=32, db_index=True, blank=True, null=True)
    # datetime when the event happened
    date = models.DateTimeField(db_index=True)
    # type of actions displayed as string
    action_type = models.CharField(max_length=32)
    story_points = models.IntegerField(null=True, default=0)

    # when copying cards, this is the original card, not the newly created one
    card = models.ForeignKey(Card, models.CASCADE, related_name="actions")
    # present list
    list = models.ForeignKey(List, models.CASCADE, default=None, null=True, blank=True,
                             related_name="card_actions")
    board = models.ForeignKey(Board, models.CASCADE, related_name="card_actions")

    is_archived = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    event = models.OneToOneField(CardActionEvent, models.CASCADE, related_name="card_action")

    objects = CardActionManager.from_queryset(CardActionQuerySet)()

    class Meta:
        get_latest_by = "date"

    def __unicode__(self):
        return "[%s list=%s] %s %s" % (self.action_type, self.list, self.card, self.date)

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
    def data(self):
        """ backwards compat """
        return self.event.data

    @property
    def list_id_and_name(self):
        d = self.data["data"].get("list", {})
        return d.get("id", None), d.get("name", None)

    @property
    def list_name(self):
        return self.event.list_name

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
        """
        name of card during time of this event

        do NOT use this if you need latest card name (most of the time you need latest card name)
        """
        return self.event.card_name

    @classmethod
    def get_story_points(cls, card_name):
        """
        find number of story points in a card name; the name usually starts with it: "(7)..."

        :param card_name: str
        :return: str
        """
        if not card_name:
            return
        regex = r"^\s*\((\d+)\)"
        try:
            return re.findall(regex, card_name)[0]
        except IndexError:
            return None

    # TODO: this takes minutes!!! move it to a different module and minimize database queries
    @classmethod
    def from_trello_response_list(cls, board, actions):
        logger.debug("processing %d actions", len(actions))
        for action_data in actions:
            with transaction.atomic():
                card, _ = Card.objects.get_or_create(trello_id=action_data["data"]["card"]["id"])
                card.save()

                event = CardActionEvent(data=action_data)
                event.save()
                ca = CardAction(
                    trello_id=action_data.get("id", None),
                    date=parse_datetime(action_data["date"]),
                    action_type=action_data["type"],
                    card=card,
                    event=event,
                    board=board  # TODO: use board from action_data
                )

                if ca.card_name and card.name != ca.card_name:
                    card.name = ca.card_name[:255]  # some users are just fun
                    card.save()

                previous_action = CardAction.objects.latest_for_card(card)
                story_points_str = CardAction.get_story_points(ca.card_name)
                story_points_int = 0
                if story_points_str is not None:
                    story_points_int = int(story_points_str)
                    ca.story_points = story_points_int

                # figure out list_name, archivals, removals and unicorns
                if ca.action_type in ["createCard", "moveCardToBoard", "defaultCard",
                                      "copyCard", "convertToCardFromCheckItem"]:  # create-like events
                    if ca.trello_board_id != board.trello_id:
                        logger.info("card %s was created on board %s",
                                    ca.trello_card_id, ca.trello_board_id)
                        # we don't care about such state
                        continue
                    # when list is changed (or on different board), name is missing; fun stuff!
                    trello_list_id, list_name = ca.list_id_and_name
                    if not trello_list_id:
                        logger.warning("list not specified for card '%s'", card.name)
                        # wat?! how about telling us to which list this is going
                        continue
                    ca.list = List.get_or_create_list(trello_list_id, list_name)

                elif ca.action_type in ["updateCard"]:  # update = change list, board, close or open
                    if ca.archiving:
                        ca.list = None
                        ca.is_archived = True
                    elif ca.opening or ca.rename:
                        # card is opened again
                        trello_list_id, list_name = ca.list_id_and_name
                        if not trello_list_id:
                            logger.warning("card updated to unknown list: %s", ca)
                            # cards without lists are useless to us; srsly trello?!
                            continue
                        ca.list = List.get_or_create_list(trello_list_id, list_name)
                        if previous_action:
                            if previous_action.list != ca.list:
                                logger.info("sneaky list change %s: %s -> %s", card, previous_action.list, ca.list)
                            elif ca.story_points == previous_action.story_points:
                                # just name update, we don't care about that
                                continue
                    else:
                        if previous_action and previous_action.is_archived:
                            logger.info("archived card %s is being moved", card)
                            continue
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

                event.processed_well = True
                event.save()
                ca.save()

                # ListStats
                if ca.rename and previous_action and previous_action.list == ca.list:
                    diff = 0
                    try:
                        current_list_stat = ListStat.objects.latest_stat_for_list(ca.list)
                        cards_rt = current_list_stat.cards_rt
                        sp_rt = current_list_stat.story_points_rt
                    except ObjectDoesNotExist:
                        cards_rt = 0
                        sp_rt = 0
                    previous_points = getattr(previous_action, "story_points", 0)
                    ListStat.create_stat(ca, ca.list, diff, cards_rt,
                                         sp_rt - previous_points + story_points_int)
                else:
                    if previous_action:
                        diff = -1
                        previous_list = previous_action.list
                        if previous_list:
                            if previous_list == ca.list:
                                # HACK: likely trello trashed an event of moving the card
                                logger.warning("card %s is already on list %s", card, previous_list)
                            previous_list_stat = ListStat.objects.latest_stat_for_list(previous_list)
                            cards_rt = previous_list_stat.cards_rt
                            sp_rt = previous_list_stat.story_points_rt
                            ListStat.create_stat(ca, previous_list, diff, cards_rt + diff,
                                                 sp_rt - previous_action.story_points)
                    if ca.list and not (ca.is_archived or ca.is_deleted):
                        diff = 1
                        try:
                            current_list_stat = ListStat.objects.latest_stat_for_list(ca.list)
                            cards_rt = current_list_stat.cards_rt
                            sp_rt = current_list_stat.story_points_rt
                        except ObjectDoesNotExist:
                            cards_rt = 0
                            sp_rt = 0
                        ListStat.create_stat(ca, ca.list, diff, cards_rt + diff,
                                             sp_rt + story_points_int)


class SprintQuerySet(models.QuerySet):
    def for_board(self, board):
        return self.filter(board=board)

    def completed(self):
        return self.filter(completed_list__isnull=False)

    def in_range(self, beginning, end):
        q = {}
        if beginning:
            q["start_dt__gt"] = beginning
        if end:
            q["end_dt__lt"] = end
        return self.filter(**q)

    def recent(self):
        return self.order_by("-end_dt")


class SprintManager(models.Manager):
    def for_board_by_end_date(self, board):
        return self.for_board(board).recent()

    def for_board_in_range_by_end_date(self, board, beginning, end):
        return self.for_board_by_end_date(board).in_range(beginning, end)

    def for_board_last_n(self, board, n):
        return self.for_board_by_end_date(board).recent()[:n]

    def latest_for_board(self, board):
        try:
            return self.for_board(board).latest()
        except ObjectDoesNotExist:
            return None

    def latest_completed(self, board):
        try:
            return self.for_board(board).completed().latest()
        except ObjectDoesNotExist:
            return None


class Sprint(models.Model):
    """

    """
    start_dt = models.DateTimeField(db_index=True, blank=True, null=True, help_text="Start date")
    end_dt = models.DateTimeField(db_index=True, blank=True, null=True, help_text="End date")
    name = models.CharField(max_length=255, blank=True, null=True)
    sprint_number = models.IntegerField(db_index=True)
    board = models.ForeignKey(Board, models.CASCADE, related_name="sprints")
    # list with completed cards for the sprint
    completed_list = models.OneToOneField(List, models.DO_NOTHING, related_name="sprint",
                                          blank=True, null=True)
    due_card = models.OneToOneField(Card, models.DO_NOTHING, related_name="sprint",
                                    blank=True, null=True)
    # cards which are part of sprint: all cards present on Next column when the sprint starts
    # this needs to be calculated from scratch when start date is changed
    cards = models.ManyToManyField(Card, related_name="sprints")

    objects = SprintManager.from_queryset(SprintQuerySet)()

    class Meta:
        get_latest_by = "end_dt"

    def __unicode__(self):
        tz = timezone.get_current_timezone()
        s = e = "<missing>"
        # TODO: display only date, not time
        if self.start_dt:
            s = tz.normalize(self.start_dt).strftime(DATETIME_FORMAT)
        if self.end_dt:
            e = tz.normalize(self.end_dt).strftime(DATETIME_FORMAT)
        return "%s (%s - %s)" % (self.name, s, e)

    def story_points_committed(self, commitment_cols):
        return ListStat.objects.sum_sp_for_list_names_before(
            self.board, commitment_cols, self.start_dt)

    @property
    def story_points_done(self):
        if not self.completed_list:
            return 0
        return self.completed_list.story_points

    def set_sprint_cards(self):
        self.cards.clear()
        card_actions = CardAction.objects.card_actions_on_list_names_in(
            self.board, ["Next"], self.start_dt)
        self.cards.add(*[x.card for x in card_actions])

    @classmethod
    def refresh(cls, board, token):
        """
        calculate sprints based on "Sprint \d+" card
        :param board:
        :return:
        """
        trello_card_ids = CardAction.objects.get_sprint_trello_card_ids(board)

        due_dict = Harvestor(token).get_due_of_cards(trello_card_ids)
        due_list = due_dict.items()

        sprint_number_re = re.compile(r"(\d+)")

        bm = KeyVal.objects.board_messages(board)
        board_messages = bm.value["messages"]
        # reset messages
        board_messages[:] = []  # python 2 list doesn't have clear()

        for trello_card_id, due_date in sorted(due_list, key=lambda x: x[1]):
            try:
                with transaction.atomic():
                    try:
                        due = due_dict[trello_card_id]
                    except KeyError:
                        logger.error("couldn't figure out due of card %s",
                                     trello_card_id)
                        continue
                    try:
                        first = CardAction.objects.for_trello_card_id_on_list_names(
                            trello_card_id, SPRINT_CARDS_ACTIVE).latest()
                    except ObjectDoesNotExist:
                        logger.info("card %s never reached In Progress",
                                    trello_card_id)
                        continue
                    card = first.card

                    sprint_number = sprint_number_re.findall(card.name)[0]
                    sprint, created = cls.objects.get_or_create(
                        board=board, sprint_number=sprint_number)

                    if created and hasattr(card, "sprint"):
                        if card.name != card.sprint.name:
                            logger.warning("duplicate sprint card detected: %s", card)
                            board_messages.append({
                                "message": (
                                    "Card \"%s\" is already assigned to sprint \"%s\". "
                                    "This is likely caused by having only a single card and "
                                    "renaming it for every sprint. Please create new cards for "
                                    "every sprint. You can do that even now, then sync the board "
                                    "and adjust sprint range in sprint detail."
                                ) % (
                                    card.name, card.sprint.name
                                )
                            })
                            continue

                    logger.debug("new sprint: %s", card)

                    # update or set
                    sprint.start_dt = first.date
                    sprint.end_dt = parse_datetime(due)
                    sprint.name = card.name
                    sprint.due_card = card
                    sprint.save()
            except DatabaseError as ex:
                # this can happen if the due card is moved to another board
                logger.error("can't create sprint: %s", ex)
                continue

            logger.debug("%s", sprint)
        bm.save()

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


@receiver(post_save, sender=Sprint)
def set_sprint_cards_cb(instance, *args, **kwargs):
    instance.set_sprint_cards()
