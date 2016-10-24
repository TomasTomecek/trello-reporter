"""
Calculate chart data

TODO:

 * move all queries to models.py
 * refactor date/time - create util functions, use timezone everywhere
"""
from __future__ import unicode_literals, print_function

import logging
import datetime

import itertools
from django.utils import timezone

from trello_reporter.charting.forms import CARDS_FORM_ID, STORY_POINTS_FORM_ID
from trello_reporter.charting.models import CardAction, ListStat

logger = logging.getLogger(__name__)


def h_f(v):
    """"humanize float"""
    return "{:.1f}".format(v)


class ChartExporter(object):
    """
    Export selected data as a chart for specific charting javascript library
    """

    @classmethod
    def cumulative_chart_c3(cls, board, lists_filter, beginning, end, delta, c_unit):
        """
        area diagram which shows number of cards in a given list per day
        """
        now = timezone.now()
        if not end:
            end = now

        response = []

        # c3 doesn't handle disconnected area segments, hence we need to cumulate
        d = beginning
        while True:
            if d > end:
                break
            stats = ListStat.objects.stats_for_list_names_before(board, lists_filter, d)
            tick = {
                "date": d.strftime("%Y-%m-%d %H:%M"),
            }
            for s in stats:
                if c_unit == CARDS_FORM_ID:
                    tick[s.list.name] = s.cards_rt
                elif c_unit == STORY_POINTS_FORM_ID:
                    tick[s.list.name] = s.story_points_rt
            response.append(tick)
            d += delta
        return response

    @classmethod
    def burndown_chart_c3(cls, board, beginning, end, in_progress_list_names):
        completed_lists = ["Complete"]
        now = timezone.now()
        if not end:
            end = now

        response = []
        delta = datetime.timedelta(days=1)
        d = beginning
        while True:
            if d > end:
                break
            if d > now:
                response.append({"date": end.strftime("%Y-%m-%d %H:%M"), "ideal": 0})
                break
            prev = d - delta
            compl = CardAction.objects.card_actions_on_list_names_in_range(
                board, completed_lists, prev, d)
            in_progress = ListStat.objects.sum_sp_for_list_names_before(
                board, in_progress_list_names, d)
            tick = {
                "date": d.strftime("%Y-%m-%d %H:%M"),
                "done": sum([x.story_points for x in compl]),
                "not_done": in_progress,
                "done_cards": [{"name": x.card.name, "id": x.card_id} for x in compl]
            }
            if len(response) == 0:
                tick["ideal"] = ListStat.objects.sum_sp_for_list_names_before(
                    board, in_progress_list_names, d)
            response.append(tick)
            d += delta
        if response:
            response[-1]["ideal"] = 0
        return response

    @classmethod
    def velocity_chart_c3(cls, sprints, commitment_cols):
        response = []
        response_len = 0
        for sprint in reversed(sprints):
            logger.debug("processing sprint %s", sprint)
            done = sprint.story_points_done
            r = {
                "done": done,
                "committed": sprint.story_points_committed(commitment_cols),
                "name": sprint.name,
            }
            # http://math.stackexchange.com/a/106314
            if response_len == 0:
                r["average"] = done
            else:
                r["average"] = (
                    ((float(response_len) * response[-1]["average"]) + done)
                    /
                    float(response_len + 1))
            response.append(r)
            response_len += 1
        return response

    @classmethod
    def list_history_chart_c3(cls, li, beginning, end):
        response = []
        for ls in ListStat.objects.for_list_in_range(li, beginning, end):
            r = {
                "cards": ls.cards_rt,
                "story_points": ls.story_points_rt,
                "date": ls.card_action.date.strftime("%Y-%m-%d %H:%M")
            }
            response.append(r)
        return response


class ControlChart(object):
    def __init__(self, board, lists_filter, beginning, end):
        logger.debug("control chart: board %s, workflow %s, range %s - %s",
                     board, lists_filter, beginning, end)
        self.board = board
        self.lists_filter = lists_filter
        self.beginning = beginning
        self.end = end
        self._chart_data = None

    @property
    def chart_data(self):
        if self._chart_data is None:
            card_actions = CardAction.objects.card_actions_on_list_names_in_interval_order_desc(
                self.board,
                itertools.chain(*self.lists_filter),
                self.beginning, self.end)

            # card -> {
            #  visited_idx: 3
            #  data: [ca, ca, ...]
            # }
            card_history = {}
            lists_filter_len = len(self.lists_filter)

            for ca in card_actions:
                if ca.rename and not ca.is_a_list_change:
                    # ignore card sizing events
                    continue

                card = ca.card

                card_data = card_history.get(card,
                                             {"visited_idx": lists_filter_len - 1, "data": []})
                card_history.setdefault(card, card_data)
                if card_data["visited_idx"] == -1:
                    # fulfilled
                    continue
                needed_state = self.lists_filter[card_data["visited_idx"]]
                assert isinstance(needed_state, list)
                if ca.list.name in needed_state:  # we need to reach this one
                    card_data["visited_idx"] -= 1
                    card_data["data"].insert(0, ca)

            self._chart_data = []
            valid_cards = {card: card_data
                           for card, card_data in card_history.items()
                           if card_data["visited_idx"] == -1}

            for card, card_data in valid_cards.items():
                first_action = card_data["data"][0]
                last_action = card_data["data"][-1]
                total_seconds = (last_action.date - first_action.date).total_seconds()
                days = float(total_seconds) / 60 / 60 / 24
                days_out = "{:.1f}".format(days)
                date = last_action.date.strftime("%Y-%m-%d %H:%M")
                self._chart_data.append({
                    "days": days_out,
                    "days_float": days,
                    "id": card.id,
                    "name": card.name,
                    "size": last_action.story_points,
                    "label": "Hours",
                    "date": date,
                    "trello_card_short_id": last_action.event.card_short_id,
                })
        return self._chart_data

    def render_stats(self):
        """
        stats for selected interval: min, max, avg
        lead/cycle/reaction time is not hardcoded - user has to pick the workflow

        :return: string, raw html
        """
        logger.debug("control chart stats")
        if not self.chart_data:
            return {"min": 0, "max": 0, "avg": 0}

        return {
            "min": h_f(min(self.chart_data, key=lambda x: x["days_float"])["days_float"]),
            "max": h_f(max(self.chart_data, key=lambda x: x["days_float"])["days_float"]),
            "avg": h_f(sum([x["days_float"] for x in self.chart_data]) / len(self.chart_data))
        }
