from __future__ import unicode_literals

import logging

import datetime
import re

from dateutil.tz import tzutc
from django.core.urlresolvers import reverse
from django.http.response import JsonResponse
from django.shortcuts import render, redirect

from trello_reporter.charting.forms import Workflow, DateForm, BurndownForm
from trello_reporter.charting.models import Board, CardAction, List, Card, Sprint
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


def show_burndown_chart(request, board_id):
    board = Board.objects.get_by_id(board_id)
    n = datetime.datetime.now()
    from_dt = n - datetime.timedelta(days=30)
    initial = {
        "from_dt": from_dt,
        "to_dt": n,
    }
    form = BurndownForm(initial=initial)
    context = {
        "form": form,
        "board": board,
        "chart_url": "burndown-chart-data"
    }
    return render(request, "charting.html", context)


def show_velocity_chart(request, board_id):
    board = Board.objects.get_by_id(board_id)
    context = {
        "board": board,
        "chart_url": "velocity-chart-data"
    }
    return render(request, "charting.html", context)


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
    now = datetime.datetime.now(tz=tzutc())
    beginning = now - datetime.timedelta(days=30)
    delta = datetime.timedelta(days=1)
    end = now

    order = []
    all_lists = List.get_all_listnames_for_board(board_id)

    if request.method == "POST":
        form = Workflow(request.POST)
        if form.is_valid():
            beginning = form.cleaned_data["from_dt"]
            end = form.cleaned_data["to_dt"]
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

            idx = 1
            while True:
                wf_key = "workflow-%d" % idx
                try:
                    value = request.POST[wf_key].strip()
                except KeyError:
                    logger.info("workflow key %s not found", wf_key)
                    break
                if value not in all_lists:
                    raise Exception("List %s is not in board" % value)
                order.append(value)
                idx += 1

            lists = List.get_lists(board_id, f=order)
        else:
            logger.warning("form is not valid")
            raise Exception("Invalid form.")
    else:
        lists = List.get_lists(board_id)
        order = all_lists

    logger.debug("lists = %s", lists)
    # we can't filter by list IDs because there may be multiple lists with the same name
    data = ChartExporter.cumulative_chart_c3(order, beginning, end, delta)
    order.sort(reverse=True)  # c3 wants it the other way around: first one is the bottom one
    response = {
        "data": data,
        "order": order,
        "all_lists": all_lists
    }
    return JsonResponse(response)


def burndown_chart_data(request, board_id):
    board = Board.objects.get(id=board_id)
    if request.method == "POST":
        form = BurndownForm(request.POST)
        if form.is_valid():
            from_dt = form.cleaned_data["from_dt"]
            to_dt = form.cleaned_data["to_dt"]
            interval, _ = board.group_card_movements(beginning=from_dt, end=to_dt)
        else:
            logger.warning("form is not valid")
            raise Exception("Invalid form.")
    else:
        interval, _ = board.group_card_movements()
    data = ChartExporter.burndown_chart_c3(interval)
    response = {
        "data": data,
    }
    return JsonResponse(response)


def velocity_chart_data(request, board_id):
    lists = List.sprint_lists_for_board(board_id)
    data = ChartExporter.velocity_chart_c3(lists)
    response = {
        "data": data
    }
    return JsonResponse(response)


def list_history_data(request, list_id):
    li = List.objects.get(id=list_id)
    data = ChartExporter.list_history_chart_c3(li)
    response = {
        "data": data
    }
    return JsonResponse(response)


def board_detail(request, board_id):
    board = Board.objects.get(id=board_id)
    lists = List.get_lists(board_id)
    sprints = Sprint.objects.filter(board__id=board_id).order_by("start_dt")
    context = {
        "board": board,
        "lists": lists,
        "sprints": sprints,
    }
    return render(request, "board_detail.html", context)


def board_refresh(request, board_id):
    board = Board.objects.get(id=board_id)
    board.ensure_actions()
    return redirect('board-detail', board_id=board_id)


def list_detail(request, list_id):
    li = List.objects.get(id=list_id)
    context = {
        "list": li,
        "chart_url": "list-history-chart-data",
        "breadcrumbs": [
            {
                "url": reverse("board-detail", args=(li.latest_action.board.id, )),
                "text": "Board \"%s\"" % li.latest_action.board.name
            },
            {
                "text": "List \"%s\"" % li.name
            },
        ]
    }
    return render(request, "list_detail.html", context)


def card_detail(request, card_id):
    card = Card.objects.get(id=card_id)
    context = {
        "card": card,
        "actions": card.actions.order_by("date"),
        "breadcrumbs": [
            {
                "url": reverse("board-detail", args=(card.latest_action.board.id, )),
                "text": "Board \"%s\"" % card.latest_action.board.name
            },
            {
                "text": "Card \"%s\"" % card.latest_action.card_name
            },
        ]
    }
    return render(request, "card_detail.html", context)


# API


def api_get_card(request, card_id):
    card = Card.objects.get(id=card_id)

    response = {
        "id": card.id,
        "name": card.latest_action.card_name,  # TODO: store the same as for lists
        "url": request.build_absolute_uri(reverse('card-detail', args=(card_id, ))),
    }
    return JsonResponse(response)
