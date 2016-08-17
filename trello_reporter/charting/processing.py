"""
Calculate chart data

TODO:

 * move all queries to models.py
"""
from __future__ import unicode_literals, print_function

import logging

import datetime

from dateutil.tz import tzutc

from trello_reporter.charting.models import CardAction, ListStat

logger = logging.getLogger(__name__)


class ChartExporter(object):
    """
    Export selected data as a chart for specific charting javascript library
    """

    @classmethod
    def cumulative_chart_c3(cls, board, lists_filter, beginning, end, delta):
        """
        area diagram which shows number of cards in a given list per day
        """

        response = []

        # # c3 doesn't handle this implementation: it can't stack disconnected area segments
        # # initial data, left-most
        # stats = ListStat.stats_for_lists_before(list_ids, beginning)
        # for s in stats:
        #     tick = {
        #         "date": beginning.strftime("%Y-%m-%d %H:%M:%S"),
        #         s.list.name: s.running_total
        #     }
        #     response.append(tick)
        # # whole interval
        # stats = ListStat.stats_for_lists_in(list_ids, beginning, end)
        # for s in stats:
        #     tick = {
        #         "date": s.card_action.date.strftime("%Y-%m-%d %H:%M:%S"),
        #         s.list.name: s.running_total
        #     }
        #     response.append(tick)
        # # right-most
        # stats = ListStat.stats_for_lists_before(list_ids, end)
        # for s in stats:
        #     tick = {
        #         "date": end.strftime("%Y-%m-%d %H:%M:%S"),
        #         s.list.name: s.running_total
        #     }
        #     response.append(tick)

        d = beginning
        while True:
            if d > end:
                break
            stats = ListStat.objects.stats_for_list_names_before(board, lists_filter, d)
            tick = {
                "date": d.strftime("%Y-%m-%d %H:%M"),
            }
            for s in stats:
                tick[s.list.name] = s.story_points_rt
            response.append(tick)
            d += delta
        return response

    @classmethod
    def control_flow_c3(cls, board):
        card_actions = CardAction.objects.actions_for_board(board.id)
        # card -> [action, action]
        card_history = {}

        logger.debug("board has %d actions", card_actions.count())

        for ca in card_actions:
            card_history.setdefault(ca.card, [])
            card_history[ca.card].insert(0, ca)
        cards = []
        for card, actions in card_history.items():
            if len(actions) <= 1:
                continue
            else:
                hours = int((actions[-1].date - actions[0].date).total_seconds() / 3600)
                date = actions[-1].date.strftime("%Y-%m-%d")
                cards.append({"hours": hours, "id": card.id, "label": "Hours", "date": date})
        return cards

    @classmethod
    def burndown_chart_c3(cls, board, beginning, end):
        in_progress_lists = ["Next", "In Progress"]
        completed_lists = ["Complete", "Completed"]
        now = datetime.datetime.now(tz=tzutc())

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
            compl = ListStat.objects.sum_sp_for_list_names_in_interval(
                board, completed_lists, prev, d)
            logger.debug("%s - %s: %d", prev, d, compl)
            in_progress = ListStat.objects.sum_sp_for_list_names_before(
                board, in_progress_lists, d)
            tick = {
                "date": d.strftime("%Y-%m-%d %H:%M"),
                "done": compl,
                "not_done": in_progress,
            }
            if len(response) == 0:
                tick["ideal"] = ListStat.objects.sum_sp_for_list_names_before(
                    board, in_progress_lists, beginning)
            response.append(tick)
            d += delta
        if response:
            response[-1]["ideal"] = 0
        return response

    @classmethod
    def velocity_chart_c3(cls, lists):
        response = []
        for li in lists:
            logger.debug("processing list %s", li)
            ls = li.latest_stat
            r = {
                "story_points": ls.story_points_rt,
                "cards_num": ls.cards_rt,
                "name": li.name,
                # "commited": 0  TODO
            }
            response.append(r)
        return response

    @classmethod
    def list_history_chart_c3(cls, li):
        response = []
        for ls in li.stats.select_related("card_action").order_by("card_action__date"):
            r = {
                "cards": ls.cards_rt,
                "story_points": ls.story_points_rt,
                "date": ls.card_action.date.strftime("%Y-%m-%d %H:%M")
            }
            response.append(r)
        return response