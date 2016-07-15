import logging

from django.http.response import JsonResponse
from django.shortcuts import render

from trello_reporter.charting.models import Board
from trello_reporter.charting.processing import ChartExporter


logger = logging.getLogger(__name__)


def index(request):
    boards = Board.list_boards()
    return render(request, "index.html", {"boards": boards})


def chart(request, board_id):
    board = Board.objects.get(id=board_id)
    return render(request, "charting.html", {"board": board})


def cumulative_chart(request, board_id):
    board = Board.objects.get(id=board_id)
    interval, lists = board.group_card_movements()
    data = ChartExporter.cumulative_chart_c3(interval, lists)
    logger.debug(data)
    import json
    logging.debug(json.dumps(data))
    return JsonResponse(data, safe=False)  # FIXME: return dict, not list
