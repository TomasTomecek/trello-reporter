from __future__ import unicode_literals, print_function


class ChartExporter(object):
    """
    Export selected data as a chart for specific charting javascript library
    """

    @classmethod
    def cumulative_chart_c3(cls, data, lists):
        """
        area diagram which shows number of cards in a given list per day

        :param data: dict: {day -> {list -> count}}
        :param lists: list of str, name of lists in specific interval

        :return:
        c3 requires output like this:

        [["x", "2016-01-01", ...],
        ["New", 4, 5, 6, ...],
        ["In Progress", 3, 6, 0, ...],
        """
        # list_name -> [val, val, val]
        stats = {x: [] for x in lists}

        idx = 0
        for day, v in data.items():
            for state in stats.keys():
                try:
                    stats[state].insert(idx, v[state])
                except KeyError:
                    stats[state].insert(idx, 0)
            idx += 1

        response = [
            ["x"] + [day.strftime("%Y-%m-%d") for day in data.keys()],
            ]
        for day, counts in stats.items():
            response.append([day] + counts)
        return response
