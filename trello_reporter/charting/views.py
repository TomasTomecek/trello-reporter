import logging

import datetime
import re
from collections import OrderedDict

from django.http.response import JsonResponse
from django.shortcuts import render

from trello_reporter.charting.forms import Workflow
from trello_reporter.charting.models import Board
from trello_reporter.charting.processing import ChartExporter


logger = logging.getLogger(__name__)


def index(request):
    boards = Board.list_boards()
    return render(request, "index.html", {"boards": boards})


def chart(request, board_id):
    n = datetime.datetime.now()
    from_dt = n - datetime.timedelta(days=30)
    # TODO [DRY]: use exactly same variables for charting
    initial = {
        "from_dt": from_dt,
        "to_dt": n,
        "count": 1,
        "time_type": "m"
    }
    form = Workflow(initial=initial)
    board = Board.objects.get(id=board_id)
    return render(request, "charting.html", {"board": board, "form": form})


def cumulative_chart(request, board_id):
    board = Board.objects.get(id=board_id)
    workflow = None
    if request.method == "POST":
        form = Workflow(request.POST)
        if form.is_valid():
            from_dt = form.cleaned_data["from_dt"]
            to_dt = form.cleaned_data["to_dt"]
            count = form.cleaned_data["count"]
            time_type = form.cleaned_data["time_type"]

            if time_type == "d":
                delta = datetime.timedelta(days=count)
            elif time_type == "m":
                delta = datetime.timedelta(days=count * 30)
            elif time_type == "h":
                delta = datetime.timedelta(seconds=count * 3600)
            else:
                raise Exception("Invalid time measure.")

            workflow = OrderedDict()
            regex = re.compile(r"workflow-(\d+)-\d+")
            for key, value in request.POST.items():
                # it's easy to send empty input
                value = value.strip()
                if value and key.startswith("workflow"):
                    try:
                        k = regex.findall(key)[0]
                    except IndexError:
                        logger.warning("starts with workflow, but doesn't match regex: %s", key)
                        continue
                    workflow.setdefault(k, [])
                    workflow[k].append(value)

            interval, lists = board.group_card_movements(
                beginning=from_dt,
                end=to_dt,
                time_span=delta,
            )
        else:
            logger.warning("form is not valid")
            raise Exception("Invalid form.")
    else:
        interval, lists = board.group_card_movements()
    data, order = ChartExporter.cumulative_chart_c3(interval, lists, workflow=workflow)
    response = {
        "data": data,
        "order": order,
        "all_lists": lists
    }
    logger.debug(response)
    return JsonResponse(response)
