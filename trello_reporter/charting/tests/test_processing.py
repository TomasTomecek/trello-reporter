from __future__ import unicode_literals

import json

import pytest

from trello_reporter.charting.models import CardAction, Board, ListStat
from data import faulty_move_to_board
from trello_reporter.charting.tests.data import undetected_name_change
from trello_reporter.harvesting.models import CardActionEvent


@pytest.mark.django_db
def test_card_actions_creation():
    b = Board(trello_id="5277b65546e5ca917f00939d", name="board name")
    b.save()
    actions = json.loads(faulty_move_to_board)
    CardAction.from_trello_response_list(b, actions)

    lss = ListStat.objects.all().order_by("card_action__date").select_related(
        "card_action", "card_action__list")

    assert lss[0].diff == 1
    assert lss[0].cards_rt == 1
    assert lss[0].story_points_rt == 0
    assert lss[0].list.name == "Next"

    # story points 0 -> 3
    assert lss[1].diff == 0
    assert lss[1].cards_rt == 1
    assert lss[1].story_points_rt == 3
    assert lss[1].list.name == "Next"

    # story points 3 -> 5
    assert lss[2].diff == 0
    assert lss[2].cards_rt == 1
    assert lss[2].story_points_rt == 5
    assert lss[2].list.name == "Next"

    # the faulty event: move from board where it wasn't suppose to be
    assert lss[3].diff + lss[4].diff == 0
    assert lss[3].cards_rt + lss[4].cards_rt == 1
    assert lss[3].story_points_rt + lss[4].story_points_rt == 5
    assert lss[3].card_action.list.name == "New"
    assert {lss[3].list.name, lss[4].list.name} == {"Next", "New"}

    # remove story points
    assert lss[5].diff == 0
    assert lss[5].cards_rt == 1
    assert lss[5].story_points_rt == 0
    assert lss[5].list.name == "New"

    # New -> Backlog
    assert lss[6].diff + lss[7].diff == 0
    assert lss[6].cards_rt + lss[7].cards_rt == 1
    assert lss[6].story_points_rt + lss[7].story_points_rt == 0
    assert lss[6].card_action.list.name == "Backlog"
    assert {lss[6].list.name, lss[7].list.name} == {"Backlog", "New"}

    # Backlog -> Next
    assert lss[8].diff + lss[9].diff == 0
    assert lss[8].cards_rt + lss[9].cards_rt == 1
    assert lss[8].story_points_rt + lss[9].story_points_rt == 0
    assert lss[8].card_action.list.name == "Next"
    assert {lss[8].list.name, lss[9].list.name} == {"Next", "Backlog"}

    # archive
    assert lss[10].diff == -1
    assert lss[10].cards_rt == 0
    assert lss[10].story_points_rt == 0
    assert lss[10].list.name == "Next"
    assert lss[10].card_action.list is None
    assert lss[10].card_action.is_archived


@pytest.mark.django_db
def test_card_actions_creation():
    b = Board(trello_id="57a9a7b40926fa6762fc07a6", name="board name")
    b.save()
    actions = json.loads(undetected_name_change)
    CardAction.from_trello_response_list(b, actions)

    cas = CardAction.objects.all().order_by("date").select_related("card", "event")

    assert cas[0].card.name == "Sprint 13"

    events = CardActionEvent.objects.all().by_date()
    assert events[0].card_name == "Sprint 12"
    assert events[0].card_name == "Sprint 13"
