from __future__ import unicode_literals

import logging

import datetime
import re

from django.http.response import JsonResponse
from django.shortcuts import render

from trello_reporter.charting.forms import Workflow, DateForm
from trello_reporter.charting.models import Board, CardAction
from trello_reporter.charting.processing import ChartExporter


logger = logging.getLogger(__name__)


def index(request):
    boards = Board.list_boards()
    return render(request, "index.html", {"boards": boards})


def show_control_chart(request, board_id):
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
    board = Board.objects.get_by_id(board_id)
    return render(request, "charting.html",
                  {"board": board, "form": form, "chart_url": "control-chart-data"})


def show_cumulative_chart(request, board_id):
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
    return render(request, "charting.html",
                  {"board": board, "form": form, "chart_url": "cumulative-chart-data"})


def card_history(request, board_id):
    board = Board.objects.get_by_id(board_id)
    card_actions = CardAction.objects.actions_for_board(board_id)
    # card -> [action, action]
    response = {}
    for ca in card_actions:
        response.setdefault(ca.card, [])
        response[ca.card].insert(0, ca)
    return render(
        request,
        "card_history.html",
        {
            "response": response,
            "board": board,
        }
    )


def cards_on_board_at(request, board_id):
    n = datetime.datetime.now()

    if request.method == "POST":
        form = DateForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data["date"]
        else:
            raise Exception("Form is not valid")
    else:
        date = n - datetime.timedelta(days=10)
        form = DateForm(initial={"date": date})

    board = Board.objects.get(id=board_id)
    card_actions = CardAction.objects.get_cards_at(board_id, date)
    # it's already ordered in sql, we can't order again
    card_actions = sorted(card_actions, key=lambda x: x.date, reverse=True)

    return render(
        request,
        "cards_on_board_at.html",
        {
            "card_actions": card_actions,
            "form": form,
            "board": board,
        }
    )


def control_chart(request, board_id):
    board = Board.objects.get(id=board_id)
    data = ChartExporter.control_flow_c3(board)
    response = {
        "data": data,
    }
    return JsonResponse(response)


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

            # idx -> { idx -> list-name }
            workflow = {}
            regex = re.compile(r"^workflow-(\d+)-(\d+)$")
            for key, value in request.POST.items():
                # it's easy to send empty input
                value = value.strip()
                if value and key.startswith("workflow"):
                    try:
                        checkpoint, idx = regex.findall(key)[0]
                    except IndexError:
                        logger.warning("starts with workflow, but doesn't match regex: %s", key)
                        continue
                    checkpoint_int = int(checkpoint)
                    workflow.setdefault(checkpoint_int, {})
                    workflow[checkpoint_int][int(idx)] = value

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
    return JsonResponse(response)
