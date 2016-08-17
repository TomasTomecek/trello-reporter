from __future__ import unicode_literals

import logging
import datetime
from urllib import urlencode

from dateutil.tz import tzutc
from django.core.urlresolvers import reverse
from django.http.response import JsonResponse
from django.shortcuts import render, redirect

from trello_reporter.charting.forms import Workflow, DateForm, BurndownForm, ControlChartForm
from trello_reporter.charting.models import Board, CardAction, List, Card, Sprint, ListStat
from trello_reporter.charting.processing import ChartExporter

logger = logging.getLogger(__name__)


def index(request):
    boards = Board.list_boards()
    return render(request, "index.html", {"boards": boards})


def show_control_chart(request, board_id):
    board = Board.objects.by_id(board_id)
    initial = {
        "sprint": Sprint.objects.latest_for_board(board)
    }
    form = ControlChartForm(initial=initial)
    form.fields['sprint'].queryset = Sprint.objects.for_board_by_end_date(board)
    context = {
        "board": board,
        "form": form,
        "chart_url": "control-chart-data"
    }
    return render(request, "charting.html", context)


def show_burndown_chart(request, board_id):
    board = Board.objects.by_id(board_id)
    initial = {
        "sprint": Sprint.objects.latest_for_board(board)
    }
    form = BurndownForm(initial=initial)
    form.fields['sprint'].queryset = Sprint.objects.for_board_by_end_date(board)
    context = {
        "form": form,
        "board": board,
        "chart_url": "burndown-chart-data"
    }
    return render(request, "charting.html", context)


def show_velocity_chart(request, board_id):
    board = Board.objects.by_id(board_id)
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
    board = Board.objects.by_id(board_id)
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
    card_actions = CardAction.objects.get_card_actions_on_board_in(board, date)
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
    board = Board.objects.by_id(board_id)
    all_lists = List.objects.get_all_listnames_for_board(board)

    if request.method == "POST":
        form = ControlChartForm(request.POST)
        if form.is_valid():
            sprint = form.cleaned_data["sprint"]
            if sprint:
                beginning = sprint.start_dt
                end = sprint.end_dt
            else:
                beginning = form.cleaned_data["from_dt"]
                end = form.cleaned_data["to_dt"]
            idx = 1
            lists_filter = []
            while True:
                wf_key = "workflow-%d" % idx
                try:
                    value = request.POST[wf_key].strip()
                except KeyError:
                    logger.info("workflow key %s not found", wf_key)
                    break
                if value not in all_lists:
                    raise Exception("List %s is not in board" % value)
                lists_filter.append(value)
                idx += 1
        else:
            # TODO: show errors
            logger.warning("form is not valid: %s", form.errors.as_json())
            raise Exception("Invalid form.")
    else:
        sprint = Sprint.objects.latest_for_board(board)
        beginning = sprint.start_dt
        end = sprint.end_dt
        lists_filter = ["Next", "Complete"]
    board = Board.objects.by_id(board_id)
    data = ChartExporter.control_flow_c3(board, lists_filter, beginning, end)
    response = {
        "data": data,
        "all_lists": all_lists
    }
    return JsonResponse(response)


def cumulative_chart(request, board_id):
    board = Board.objects.get(id=board_id)
    now = datetime.datetime.now(tz=tzutc())
    beginning = now - datetime.timedelta(days=30)
    delta = datetime.timedelta(days=1)
    end = now

    order = []
    all_lists = List.objects.get_all_listnames_for_board(board)

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

            lists = List.objects.filter_lists_for_board(board, f=order)
        else:
            logger.warning("form is not valid")
            raise Exception("Invalid form.")
    else:
        lists = List.objects.filter_lists_for_board(board)
        order = all_lists

    logger.debug("lists = %s", lists)
    # we can't filter by list IDs because there may be multiple lists with the same name
    data = ChartExporter.cumulative_chart_c3(board, order, beginning, end, delta)

    # c3 wants it the other way around: first one is the bottom one
    order = list(reversed(order))  # order may not be list, force it to be one

    response = {
        "data": data,
        "order": order,
        "all_lists": all_lists
    }
    return JsonResponse(response)


def burndown_chart_data(request, board_id):
    board = Board.objects.by_id(board_id)

    if request.method == "POST":
        form = BurndownForm(request.POST)
        if form.is_valid():
            sprint = form.cleaned_data["sprint"]
            if sprint:
                beginning = sprint.start_dt
                end = sprint.end_dt
            else:
                beginning = form.cleaned_data["from_dt"]
                end = form.cleaned_data["to_dt"]
        else:
            # TODO: show errors
            logger.warning("form is not valid: %s", form.errors.as_json())
            raise Exception("Invalid form.")
    else:
        sprint_id = request.GET.get("sprint_id", None)
        if sprint_id:
            sprint = Sprint.objects.get(id=sprint_id)
        else:
            sprint = Sprint.objects.latest_for_board(board)
        beginning = sprint.start_dt
        end = sprint.end_dt

    data = ChartExporter.burndown_chart_c3(board, beginning, end)
    response = {
        "data": data,
    }
    return JsonResponse(response)


def velocity_chart_data(request, board_id):
    board = Board.objects.by_id(board_id)
    lists = List.objects.sprint_archiving_lists_for_board(board)
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
    board = Board.objects.by_id(board_id)
    # TODO: order by name, in python
    lists = List.objects.filter_lists_for_board(board)
    sprints = Sprint.objects.filter(board__id=board_id).order_by("start_dt")
    context = {
        "board": board,
        "lists": lists,
        "sprints": sprints,
    }
    return render(request, "board_detail.html", context)


def board_refresh(request, board_id):
    board = Board.objects.by_id(board_id)
    board.ensure_actions()
    return redirect('board-detail', board_id=board_id)


def sprint_detail(request, sprint_id):
    sprint = Sprint.objects.get(id=sprint_id)
    if sprint.completed_list is not None:
        # don't supply date, we want latest stuff
        card_actions = CardAction.objects.safe_card_actions_on_list_in(
            sprint.board,
            sprint.completed_list,
        )
    else:
        card_actions = CardAction.objects.card_actions_on_list_names_in(
            sprint.board,
            ["Next", "In progress", "Complete"],
            sprint.end_dt
        )
    chart_url = reverse("burndown-chart-data", args=(sprint.board.id, ), )
    chart_url += "?" + urlencode({"sprint_id": sprint.id})
    context = {
        "sprint": sprint,
        "card_actions": card_actions,
        "chart_url": chart_url,
        "breadcrumbs": [
            {
                "url": reverse("board-detail", args=(sprint.board.id, )),
                "text": "Board \"%s\"" % sprint.board.name
            },
            {
                "text": "Sprint \"%s\"" % sprint.name
            },
        ],
    }
    return render(request, "sprint_detail.html", context)


def list_detail(request, list_id):
    li = List.objects.get(id=list_id)
    context = {
        "list": li,
        "chart_url": "list-history-chart-data",
        "list_stats": ListStat.objects.for_list_order_by_date(li),
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
