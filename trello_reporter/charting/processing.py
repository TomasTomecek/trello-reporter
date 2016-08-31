"""
Calculate chart data

TODO:

 * move all queries to models.py
 * refactor date/time - create util functions, use timezone everywhere
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

        beginning = datetime.datetime.combine(beginning, datetime.datetime.min.time())
        end = datetime.datetime.combine(end, datetime.datetime.max.time())

        d = beginning
        while True:
            if d > end:
                break
            stats = ListStat.objects.stats_for_list_names_before(board, lists_filter, d)
            tick = {
                "date": d.strftime("%Y-%m-%d %H:%M"),
            }
            for s in stats:
                tick[s.list.name] = s.cards_rt
            response.append(tick)
            d += delta
        return response

    @classmethod
    def control_flow_c3(cls, board, lists_filter, beginning, end):
        logger.debug("rendering control chart for board %s, workflow %s, range %s - %s",
                     board, lists_filter, beginning, end)
        card_actions = CardAction.objects.card_actions_on_list_names_in_interval_order_desc(
            board, lists_filter, beginning, end)

        # card -> {
        #  visited_idx: 3
        #  data: [ca, ca, ...]
        # }
        card_history = {}
        lists_filter_len = len(lists_filter)

        for ca in card_actions:
            card = ca.card

            card_history.setdefault(card, {"visited_idx": lists_filter_len - 1, "data": []})
            card_data = card_history[card]
            if card_data["visited_idx"] == -1:
                continue
            needed_state = lists_filter[card_data["visited_idx"]]
            if ca.list.name == needed_state:
                card_data["visited_idx"] -= 1
                card_data["data"].insert(0, ca)

        cards = []
        for card, card_data in card_history.items():
            if card_data["visited_idx"] > -1:
                # not fulfilled
                continue
            else:
                first_action = card_data["data"][0]
                last_action = card_data["data"][-1]
                total_seconds = (last_action.date - first_action.date).total_seconds()
                days = float(total_seconds) / 60 / 60 / 24
                days_out = "{:.1f}".format(days)
                logger.debug("%s - %s = %s days", last_action, first_action, days_out)
                date = last_action.date.strftime("%Y-%m-%d %H:%M")
                cards.append({
                    "days": days_out,
                    "id": card.id,
                    "size": last_action.story_points,
                    "label": "Hours",
                    "date": date
                })
        return cards

    @classmethod
    def burndown_chart_c3(cls, board, beginning, end):
        in_progress_lists = ["Next", "In Progress"]
        completed_lists = ["Complete", "Completed"]
        tz = tzutc()
        now = datetime.datetime.now(tz=tz)
        if end:
            if not isinstance(end, datetime.datetime):
                end = datetime.datetime(
                    year=end.year, month=end.month, day=end.day, hour=23, minute=59, tzinfo=tz)
        else:
            end = now

        response = []
        delta = datetime.timedelta(days=1)
        if not isinstance(beginning, datetime.datetime):
            d = datetime.datetime(
                year=beginning.year, month=beginning.month, day=beginning.day, hour=0, minute=0,
                tzinfo=tz)
        else:
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
            in_progress = ListStat.objects.latest_sp_for_list_names_before(
                board, in_progress_lists, d)
            tick = {
                "date": d.strftime("%Y-%m-%d %H:%M"),
                "done": sum([x.story_points for x in compl]),
                "not_done": in_progress,
                "done_cards": [{"name": x.card.name, "id": x.card_id} for x in compl]
            }
            if len(response) == 0:
                tick["ideal"] = ListStat.objects.latest_sp_for_list_names_before(
                    board, in_progress_lists, beginning)
            response.append(tick)
            d += delta
        if response:
            response[-1]["ideal"] = 0
        return response

    @classmethod
    def velocity_chart_c3(cls, sprints):
        response = []
        response_len = 0
        for sprint in reversed(sprints):
            logger.debug("processing sprint %s", sprint)
            done = sprint.story_points_done
            r = {
                "done": done,
                "committed": sprint.story_points_committed,
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