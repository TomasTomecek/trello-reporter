from __future__ import unicode_literals

import json
import logging
import datetime
from urllib import urlencode

from dateutil.tz import tzutc

from django.core.urlresolvers import reverse
from django.http.response import JsonResponse
from django.shortcuts import render, redirect
from django.views.generic.base import TemplateView, View

from trello_reporter.charting import forms
from trello_reporter.charting.models import Board, CardAction, List, Card, Sprint, ListStat
from trello_reporter.charting.processing import ChartExporter
from trello_reporter.harvesting.models import CardActionEvent

logger = logging.getLogger(__name__)

# local constants

CONTROL_INITIAL_WORKFLOW = ["Next", "Complete"]
BURNDOWN_INITIAL_WORKFLOW = ["Next", "In Progress"]
CUMULATIVE_FLOW_INITIAL_WORKFLOW = ["New", "Backlog", "Next", "In Progress", "Complete"]


def index(request):
    logger.debug("display index")
    boards = Board.list_boards(request.user, request.COOKIES["token"])
    return render(request, "index.html", {
        "boards": boards,
    })


class Breadcrumbs(object):
    @classmethod
    def text(cls, text):
        return {"text": text}

    @classmethod
    def url(cls, text):
        return {"url": text}

    @classmethod
    def board_detail(cls, board):
        t = cls.url(reverse("board-detail", args=(board.id, )))
        t.update(cls.text("Board \"%s\"" % board.name))
        return t


class BaseView(TemplateView):
    view_name = None  # for javascript


def humanize_form_errors(form, formset=None):
    texts = []
    if form.errors:
        form_errors_text = form.errors.as_text()
        logger.info("form errors: %s", form_errors_text)
        texts.append(form_errors_text)
    if formset:
        nfe = formset.non_form_errors()
        if nfe:
            nfe_text = nfe.as_text()
            logger.info("non formset errors: %s", nfe_text)
            texts.append(nfe_text)
        for fe in formset.errors:
            if fe:
                formset_form_error_text = fe.as_text()
                logger.info("formset, form error: %s", formset_form_error_text)
                texts.append(formset_form_error_text)
    return "<br>".join(texts)


class ChartView(BaseView):
    chart_name = None
    chart_data_url = None
    form_class = None
    view_name = "chart"

    def __init__(self, **kwargs):
        super(ChartView, self).__init__(**kwargs)
        # initial data populated in the form
        self.initial_form_data = {}
        # data from request.POST
        self.form_data = None
        self.formset_data = None
        self.form = None

    def get_context_data(self, **kwargs):
        context = super(ChartView, self).get_context_data(**kwargs)
        context["view_name"] = self.view_name  # django uses view to link self
        context["chart_name"] = self.chart_name
        context["chart_data_url"] = self.chart_data_url

        self.form = self.form_class(data=self.form_data, initial=self.initial_form_data)
        context["form"] = self.form
        return context

    @staticmethod
    def respond_json_form_errors(form, formset=None):
        return JsonResponse({"error": "Form is not valid: " +
                                      humanize_form_errors(form, formset=formset)})


class ControlChartBase(ChartView):
    """ common code for data and html """
    chart_name = "control"
    form_class = forms.ControlChartForm

    def get_context_data(self, board_id, **kwargs):
        board = Board.objects.by_id(board_id)
        sprint = Sprint.objects.latest_for_board(board)
        self.initial_form_data["sprint"] = sprint
        self.initial_form_data["count"] = 1
        self.initial_form_data["time_type"] = "d"

        context = super(ControlChartBase, self).get_context_data(**kwargs)
        self.form.set_sprint_choices(Sprint.objects.for_board_by_end_date(board))

        lis = List.objects.get_all_listnames_for_board(board)
        formset = forms.get_workflow_formset([("", "")] + zip(lis, lis), CONTROL_INITIAL_WORKFLOW,
                                             data=self.formset_data)

        context["board"] = board
        context["formset"] = formset
        context["latest_sprint"] = sprint
        return context


class ControlChartView(ControlChartBase):
    template_name = "chart/control_chart.html"

    def get_context_data(self, board_id, **kwargs):
        logger.debug("display control chart")

        self.chart_data_url = reverse("control-chart-data", args=(board_id, ))

        context = super(ControlChartView, self).get_context_data(board_id, **kwargs)

        context["breadcrumbs"] = [
            Breadcrumbs.board_detail(context["board"]),
            Breadcrumbs.text("Control Chart")
        ]
        return context


class ControlChartDataView(ControlChartBase):
    def post(self, request, board_id, *args, **kwargs):
        self.form_data = request.POST
        self.formset_data = request.POST
        context = super(ControlChartDataView, self).get_context_data(board_id, **kwargs)
        form, formset = context["form"], context["formset"]

        if not (form.is_valid() and formset.is_valid()):
            return self.respond_json_form_errors(form, formset=formset)
        data = ChartExporter.control_flow_c3(
            context["board"], formset.workflow, form.cleaned_data["beginning"],
            form.cleaned_data["end"])
        return JsonResponse({"data": data})


class BurndownChartBase(ChartView):
    chart_name = "burndown"
    form_class = forms.BurndownChartForm

    def get_context_data(self, board_id, **kwargs):
        board = Board.objects.by_id(board_id)
        sprint = Sprint.objects.latest_for_board(board)
        self.initial_form_data["sprint"] = sprint

        context = super(BurndownChartBase, self).get_context_data(**kwargs)
        self.form.set_sprint_choices(Sprint.objects.for_board_by_end_date(board))

        lis = List.objects.get_all_listnames_for_board(board)
        formset = forms.get_workflow_formset([("", "")] + zip(lis, lis), BURNDOWN_INITIAL_WORKFLOW,
                                             data=self.formset_data)

        context["board"] = board
        context["formset"] = formset
        context["latest_sprint"] = sprint
        return context


class BurndownChartView(BurndownChartBase):
    template_name = "chart/burndown_chart.html"

    def get_context_data(self, board_id, **kwargs):
        logger.debug("display burndown chart")

        self.chart_data_url = reverse("burndown-chart-data", args=(board_id, ))

        context = super(BurndownChartView, self).get_context_data(board_id, **kwargs)

        context["breadcrumbs"] = [
            Breadcrumbs.board_detail(context["board"]),
            Breadcrumbs.text("Burndown Chart")
        ]
        return context


class BurndownChartDataView(BurndownChartBase):
    def post(self, request, board_id, *args, **kwargs):
        logger.debug("get data for burndown chart")
        self.form_data = request.POST
        self.formset_data = request.POST
        context = super(BurndownChartDataView, self).get_context_data(board_id, **kwargs)
        form, formset = context["form"], context["formset"]

        if not (form.is_valid() and formset.is_valid()):
            return self.respond_json_form_errors(form, formset=formset)
        data = ChartExporter.burndown_chart_c3(
            context["board"], form.cleaned_data["beginning"],
            form.cleaned_data["end"], formset.workflow)
        return JsonResponse({"data": data})


class CumulativeFlowChartBase(ChartView):
    chart_name = "cumulative_flow"
    form_class = forms.CumulativeFlowChartForm

    def get_context_data(self, board_id, **kwargs):
        board = Board.objects.by_id(board_id)
        today = datetime.datetime.now().date()
        self.initial_form_data["from_dt"] = today - datetime.timedelta(days=30)
        self.initial_form_data["to_dt"] = today
        self.initial_form_data["time_type"] = "d"
        self.initial_form_data["count"] = 1

        context = super(CumulativeFlowChartBase, self).get_context_data(**kwargs)
        self.form.set_sprint_choices(Sprint.objects.for_board_by_end_date(board))

        lis = List.objects.get_all_listnames_for_board(board)
        formset = forms.get_workflow_formset([("", "")] + zip(lis, lis),
                                             CUMULATIVE_FLOW_INITIAL_WORKFLOW,
                                             data=self.formset_data)

        context["board"] = board
        context["formset"] = formset
        return context


class CumulativeFlowChartView(CumulativeFlowChartBase):
    template_name = "chart/cumulative_flow_chart.html"

    def get_context_data(self, board_id, **kwargs):
        logger.debug("display cumulative flow chart")

        self.chart_data_url = reverse("cumulative-flow-chart-data", args=(board_id, ))

        context = super(CumulativeFlowChartView, self).get_context_data(board_id, **kwargs)

        context["breadcrumbs"] = [
            Breadcrumbs.board_detail(context["board"]),
            Breadcrumbs.text("Cumulative flow chart")
        ]
        return context


class CumulativeFlowChartDataView(CumulativeFlowChartBase):
    def post(self, request, board_id, *args, **kwargs):
        logger.debug("get data for cumulative flow chart")
        self.form_data = request.POST
        self.formset_data = request.POST
        context = super(CumulativeFlowChartDataView, self).get_context_data(board_id, **kwargs)
        form, formset = context["form"], context["formset"]

        if not (form.is_valid() and formset.is_valid()):
            return self.respond_json_form_errors(form, formset=formset)
        order = formset.workflow
        data = ChartExporter.cumulative_chart_c3(
            context["board"],
            order,
            form.cleaned_data["beginning"], form.cleaned_data["end"],
            form.cleaned_data["delta"])
        # c3 wants reversed order
        return JsonResponse({"data": data, "order": list(reversed(order))})


class VelocityChartBase(ChartView):
    chart_name = "velocity"
    form_class = forms.VelocityChartForm

    def get_context_data(self, board_id, **kwargs):
        board = Board.objects.by_id(board_id)
        today = datetime.datetime.now().date()
        self.initial_form_data["from_dt"] = today - datetime.timedelta(days=180)
        self.initial_form_data["to_dt"] = today

        context = super(VelocityChartBase, self).get_context_data(**kwargs)

        context["board"] = board
        return context


class VelocityChartView(VelocityChartBase):
    template_name = "chart/velocity_chart.html"

    def get_context_data(self, board_id, **kwargs):
        logger.debug("display velocity chart")

        self.chart_data_url = reverse("velocity-chart-data", args=(board_id, ))

        context = super(VelocityChartView, self).get_context_data(board_id, **kwargs)

        context["breadcrumbs"] = [
            Breadcrumbs.board_detail(context["board"]),
            Breadcrumbs.text("Velocity Chart")
        ]
        return context


class VelocityChartDataView(VelocityChartBase):
    def post(self, request, board_id, *args, **kwargs):
        logger.debug("get data for velocity chart")
        self.form_data = request.POST
        context = super(VelocityChartDataView, self).get_context_data(board_id, **kwargs)
        form = context["form"]

        if not form.is_valid():
            return self.respond_json_form_errors(form)

        sprints = Sprint.objects.for_board_in_range_by_end_date(
            context["board"], form.cleaned_data["from_dt"], form.cleaned_data["to_dt"])
        data = ChartExporter.velocity_chart_c3(sprints)
        return JsonResponse({"data": data})


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


def list_history_data(request, list_id):
    li = List.objects.get(id=list_id)
    data = ChartExporter.list_history_chart_c3(li)
    response = {
        "data": data
    }
    return JsonResponse(response)


def board_detail(request, board_id):
    board = Board.objects.by_id(board_id)
    logger.debug("board detail %s", board)
    lists = List.objects.filter_lists_for_board(board)
    lists = sorted(lists, key=lambda x: x.name)
    sprints = Sprint.objects.filter(board__id=board_id).order_by("start_dt")
    context = {
        "board": board,
        "lists": lists,
        "sprints": sprints,
        "breadcrumbs": [
            {
                "text": "Board \"%s\"" % board.name
            }
        ],
    }
    return render(request, "board_detail.html", context)


def board_refresh(request, board_id):
    board = Board.objects.by_id(board_id)
    logger.debug("refresh board %s", board)
    board.ensure_actions(request.COOKIES["token"])
    return redirect('board-detail', board_id=board_id)


def sprint_detail(request, sprint_id):
    sprint = Sprint.objects.get(id=sprint_id)
    logger.debug("sprint detail: %s", sprint)
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
    logger.debug("list detail: %s", li)
    context = {
        "list": li,
        "view_name": "list_history",
        "chart_name": "list_history",
        "chart_data_url": reverse("list-history-chart-data", args=(list_id, )),
        "list_stats": ListStat.objects.for_list_order_by_date(li),
        "breadcrumbs": [
            {
                "url": reverse("board-detail", args=(li.latest_action.board.id, )),
                "text": "Board \"%s\"" % li.latest_action.board.name
            },
            {
                "text": "Column \"%s\"" % li.name
            },
        ]
    }
    return render(request, "list_detail.html", context)


def card_detail(request, card_id):
    card = Card.objects.get(id=card_id)
    logger.debug("card detail: %s", card)
    # (previous_action, action)
    action_list = list(card.actions.order_by("date"))
    actions = zip([None] + action_list[:-1], action_list)

    events = [json.dumps(x.data, indent=2)
              for x in CardActionEvent.objects.for_card_by_date(card.trello_id)]

    context = {
        "card": card,
        "actions": actions,
        "events": events,
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


def stalled_cards(request, list_id):
    li = List.objects.get(id=list_id)
    card_actions = CardAction.objects.safe_card_actions_on_list_in(li.latest_action.board, li)
    card_actions = sorted(card_actions, key=lambda x: x.date)
    context = {
        "list": li,
        "card_actions": card_actions,
    }
    return render(request, "stalled_cards.html", context)


# API


def api_get_card(request, card_id):
    card = Card.objects.get(id=card_id)
    logger.debug("api: get card %s", card)

    response = {
        "id": card.id,
        "name": card.name,
        "url": request.build_absolute_uri(reverse('card-detail', args=(card_id, ))),
    }
    return JsonResponse(response)
