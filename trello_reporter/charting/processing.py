"""
Calculate chart data

TODO:

 * move all queries to models.py
"""
from __future__ import unicode_literals, print_function

import logging

from trello_reporter.charting.models import CardAction, ListStat

logger = logging.getLogger(__name__)


class ChartExporter(object):
    """
    Export selected data as a chart for specific charting javascript library
    """

    @classmethod
    def cumulative_chart_c3(cls, list_ids, beginning, end, delta):
        """
        area diagram which shows number of cards in a given list per day

        :param lists: list of str, name of lists in specific interval
        """

        response = []

        # initial data, left-most
        stats = ListStat.stats_for_lists_before(list_ids, beginning)
        for s in stats:
            tick = {
                "date": beginning.strftime("%Y-%m-%d %H:%M:%S"),
                s.list.name: s.running_total
            }
            response.append(tick)
        # whole interval
        stats = ListStat.stats_for_lists_in(list_ids, beginning, end)
        for s in stats:
            tick = {
                "date": s.card_action.date.strftime("%Y-%m-%d %H:%M:%S"),
                s.list.name: s.running_total
            }
            response.append(tick)
        # right-most
        stats = ListStat.stats_for_lists_before(list_ids, end)
        for s in stats:
            tick = {
                "date": end.strftime("%Y-%m-%d %H:%M:%S"),
                s.list.name: s.running_total
            }
            response.append(tick)

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
    def burndown_chart_c3(cls, data):
        in_progress_lists = ["Next", "In Progress"]
        completed_list = "Complete"

        # {"day": day, "done": int, "not_done": int}
        stats = []
        for day, v in data.items():
            next_count = v.get(in_progress_lists[0], 0)
            in_progress_count = v.get(in_progress_lists[1], 0)
            not_done = next_count + in_progress_count
            done = v.get(completed_list, 0)
            stats.append({
                "done": done,
                "not_done": not_done,
                "date": day.strftime("%Y-%m-%d")
            })

        return stats

    @classmethod
    def velocity_chart_c3(cls, lists):
        response = []
        for li in lists:
            logger.debug("processing list %s", li)
            ls = li.latest_stat
            r = {
                "story_points": li.story_points,
                "cards_num": ls.running_total,
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
                "count": ls.running_total,
                "date": ls.card_action.date.strftime("%Y-%m-%d %H:%M")
            }
            response.append(r)
        return response