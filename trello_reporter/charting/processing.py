from __future__ import unicode_literals, print_function

import logging

from django.core.exceptions import ObjectDoesNotExist

from trello_reporter.charting.models import CardAction

logger = logging.getLogger(__name__)


class ChartExporter(object):
    """
    Export selected data as a chart for specific charting javascript library
    """

    @classmethod
    def cumulative_chart_c3(cls, data, lists, workflow=None):
        """
        area diagram which shows number of cards in a given list per day

        :param data: dict: {day -> {list -> count}}
        :param lists: list of str, name of lists in specific interval
        :param workflow: dict, mapping between checkpoints and a set of states which belongs to
                         this checkpoint
                         idx -> { idx -> list-name }

        :return:
        c3 requires output like this:

        [["x", "2016-01-01", ...],
        ["New", 4, 5, 6, ...],
        ["In Progress", 3, 6, 0, ...],
        """
        if workflow:
            logger.debug("workflow = %s", workflow)
            order = []
            idx = 1
            while True:
                try:
                    val = workflow[idx]
                except KeyError:
                    break
                else:
                    idx_in = 1
                    while True:
                        try:
                            val_in = val[idx_in]
                        except KeyError:
                            break
                        else:
                            order.append(val_in)
                            idx_in += 1
                    idx += 1
            order.reverse()

            logger.info(order)
            lists_filter = set(order)
            lists_set = set(lists)
            stats = {x: [] for x in lists_set.intersection(lists_filter)}
            diff = lists_filter.difference(lists_set)
            if diff:
                raise Exception("filter contains unknown lists: %s" % diff)
        else:
            # list_name -> [val, val, val]
            stats = {x: [] for x in lists}
            lists_filter = []
            order = lists

        for day, v in data.items():
            # TODO: don't display consecutive zeros
            for state in stats.keys():
                if workflow:
                    if state not in lists_filter:
                        continue
                try:
                    stats[state].append(v[state])
                except KeyError:
                    stats[state].append(0)

        response = [["x"] + [day.strftime("%Y-%m-%d") for day in data.keys()]]
        if workflow:
            for state in order:
                response.append([state] + stats[state])
        else:
            for state, counts in stats.items():
                response.append([state] + counts)
        return response, order

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
            r = {
                "story_points": 0,
                "cards_num": 0,
                "name": li.name,
                # "commited": 0  TODO
            }
            for card in li.cards:
                logger.debug("processing card %s", card)
                if card.is_archived or card.is_deleted:
                    continue
                try:
                    r["story_points"] += card.story_points
                except TypeError:
                    pass  # story points are not set
                r["cards_num"] += 1

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