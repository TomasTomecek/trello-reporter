from __future__ import unicode_literals, print_function

import itertools


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

        :return:
        c3 requires output like this:

        [["x", "2016-01-01", ...],
        ["New", 4, 5, 6, ...],
        ["In Progress", 3, 6, 0, ...],
        """
        if workflow:
            order = list(itertools.chain(*workflow.values()))
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

        idx = 0
        for day, v in data.items():
            # TODO: don't display consecutive zeros
            for state in stats.keys():
                if workflow:
                    if state not in lists_filter:
                        continue
                try:
                    stats[state].insert(idx, v[state])
                except KeyError:
                    stats[state].insert(idx, 0)
            idx += 1

        response = [["x"] + [day.strftime("%Y-%m-%d") for day in data.keys()]]
        if workflow:
            for checkpoint in workflow.values():
                for state in checkpoint:
                    response.append([state] + stats[state])

        for state, counts in stats.items():
            response.append([state] + counts)
        return response, order

    @classmethod
    def control_flow_c3(cls):
        pass