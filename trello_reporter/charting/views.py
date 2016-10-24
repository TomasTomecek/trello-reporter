from __future__ import unicode_literals

import datetime
import json
import logging
from urllib import urlencode

from django.core.urlresolvers import reverse
from django.http.response import JsonResponse, Http404
from django.shortcuts import render, redirect
from django.template import loader
from django.utils import timezone
from django.views.generic.base import TemplateView

from trello_reporter.authentication.models import KeyVal
from trello_reporter.charting import forms
from trello_reporter.charting.constants import CUMULATIVE_FLOW_INITIAL_WORKFLOW, COMPLETED_COLUMNS, \
    SELECTED_COLUMNS_DESCRIPTION, SPRINT_COMMITMENT_DESCRIPTION, DATA_SYNCHRONIZATION_DESCRIPTION, \
    SPRINT_CALCULATION_DESCRIPTION, BURNDOWN_CHART_DESCRIPTION, CONTROL_CHART_DESCRIPTION, \
    VELOCITY_CHART_DESCRIPTION, CUMULATIVE_FLOW_CHART_DESCRIPTION
from trello_reporter.charting.models import Board, CardAction, List, Card, Sprint, ListStat
from trello_reporter.charting.processing import ChartExporter, ControlChart
from trello_reporter.charting.templatetags.card import display_card
from trello_reporter.harvesting.models import CardActionEvent


logger = logging.getLogger(__name__)

# local constants

CONTROL_INITIAL_WORKFLOW = [["Next"], ["Complete"]]


def index(request):
    logger.debug("display index")
    boards = Board.list_boards(request.user, request.COOKIES["token"])
    return render(request, "index.html", {
        "boards": boards,
        "breadcrumbs": [Breadcrumbs.text("Boards")]
    })


class Breadcrumbs(object):
    @classmethod
    def text(cls, text):
        return {"text": text}

    @classmethod
    def url(cls, url, text):
        t = {
            "url": url,
            "text": text
        }
        return t

    @classmethod
    def boards_index(cls):
        return cls.url(reverse("index"), "Boards")

    @classmethod
    def board_detail(cls, board):
        return [
            cls.boards_index(),
            Breadcrumbs.url(reverse("board-detail", args=(board.id, )), board.name)
        ]


class BaseView(TemplateView):
    view_name = None  # for javascript


def humanize_form_errors(form_list=None, formsets=None):
    """ return html with errors in forms; should be piped into notification widget """
    texts = []
    for form in form_list:
        if form and form.errors:
            form_errors_text = form.errors.as_text()
            logger.info("form errors: %s", form_errors_text)
            texts.append(form_errors_text)
    if formsets:
        for formset in formsets:
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
    def respond_json_form_errors(form_list, formset=None):
        return JsonResponse({"error": "Form is not valid: " +
                                      humanize_form_errors(form_list, formsets=[formset])})


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
        formset = forms.get_workflow_formset(zip(lis, lis), CONTROL_INITIAL_WORKFLOW,
                                             form_class=forms.MultiWorkflowMixin,
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

        context["breadcrumbs"] = Breadcrumbs.board_detail(context["board"]) + \
            [Breadcrumbs.text("Control Chart")]
        context["control_chart_description"] = CONTROL_CHART_DESCRIPTION
        return context


class ControlChartDataView(ControlChartBase):
    def post(self, request, board_id, *args, **kwargs):
        self.form_data = request.POST
        self.formset_data = request.POST
        context = super(ControlChartDataView, self).get_context_data(board_id, **kwargs)
        form, formset = context["form"], context["formset"]

        if not (form.is_valid() and formset.is_valid()):
            return self.respond_json_form_errors([form], formset=formset)
        chart = ControlChart(
            context["board"], formset.workflow, form.cleaned_data["beginning"],
            form.cleaned_data["end"])

        data = chart.chart_data

        html = loader.render_to_string("chunks/control_chart_table.html",
                                       context=chart.render_stats())

        return JsonResponse({"data": data, "html": html})


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
        self.commitment_cols = KeyVal.objects.sprint_commitment_columns(board).value["columns"]

        com_form = forms.ListsSelectorForm(
            self.commitment_cols,
            lis,
            data=self.form_data,
        )

        context["board"] = board
        context["com_form"] = com_form
        context["latest_sprint"] = sprint
        return context


class BurndownChartView(BurndownChartBase):
    template_name = "chart/burndown_chart.html"

    def get_context_data(self, board_id, **kwargs):
        logger.debug("display burndown chart")

        self.chart_data_url = reverse("burndown-chart-data", args=(board_id, ))

        context = super(BurndownChartView, self).get_context_data(board_id, **kwargs)

        context["breadcrumbs"] = Breadcrumbs.board_detail(context["board"]) + \
            [Breadcrumbs.text("Burndown Chart")]
        context["burndown_chart_description"] = BURNDOWN_CHART_DESCRIPTION
        return context


class BurndownChartDataView(BurndownChartBase):
    def get(self, request, *args, **kwargs):
        sprint_id = request.GET.get("sprint_id", None)
        if not sprint_id:
            raise Http404("Selected view of burndown chart does not exist, please specify sprint.")
        # so self.commitment_cols is set
        super(BurndownChartDataView, self).get_context_data(*args, **kwargs)
        sprint = Sprint.objects.get(id=sprint_id)
        data = ChartExporter.burndown_chart_c3(
            sprint.board, sprint.start_dt,
            sprint.end_dt, self.commitment_cols)
        return JsonResponse({"data": data})

    def post(self, request, board_id, *args, **kwargs):
        logger.debug("get data for burndown chart")
        self.form_data = request.POST
        context = super(BurndownChartDataView, self).get_context_data(board_id, **kwargs)
        form, com_form = context["form"], context["com_form"]

        if not (form.is_valid() and com_form.is_valid()):
            return self.respond_json_form_errors(form_list=(form, com_form))
        data = ChartExporter.burndown_chart_c3(
            context["board"], form.cleaned_data["beginning"],
            form.cleaned_data["end"], com_form.workflow)
        return JsonResponse({"data": data})


class CumulativeFlowChartBase(ChartView):
    chart_name = "cumulative_flow"
    form_class = forms.CumulativeFlowChartForm

    def get_context_data(self, board_id, **kwargs):
        board = Board.objects.by_id(board_id)
        today = timezone.now().date()
        self.initial_form_data["from_dt"] = today - datetime.timedelta(days=30)
        self.initial_form_data["to_dt"] = today
        self.initial_form_data["time_type"] = "d"
        self.initial_form_data["count"] = 1

        context = super(CumulativeFlowChartBase, self).get_context_data(**kwargs)
        self.form.set_sprint_choices(Sprint.objects.for_board_by_end_date(board))

        lis = List.objects.get_all_listnames_for_board(board)
        context["all_lists"] = lis
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

        context["breadcrumbs"] = Breadcrumbs.board_detail(context["board"]) + \
            [Breadcrumbs.text("Cumulative flow chart")]
        context["cumulative_flow_chart_description"] = CUMULATIVE_FLOW_CHART_DESCRIPTION
        return context


class CumulativeFlowChartDataView(CumulativeFlowChartBase):
    def post(self, request, board_id, *args, **kwargs):
        logger.debug("get data for cumulative flow chart")
        self.form_data = request.POST
        self.formset_data = request.POST
        context = super(CumulativeFlowChartDataView, self).get_context_data(board_id, **kwargs)
        form, formset = context["form"], context["formset"]

        if not (form.is_valid() and formset.is_valid()):
            return self.respond_json_form_errors([form], formset=formset)
        order = formset.workflow
        data = ChartExporter.cumulative_chart_c3(
            context["board"],
            order,
            form.cleaned_data["beginning"], form.cleaned_data["end"],
            form.cleaned_data["delta"],
            form.cleaned_data["cards_or_sp"]
        )
        # c3 wants reversed order
        return JsonResponse({"data": data, "order": list(reversed(order)),
                             "all_lists": context["all_lists"]})


class VelocityChartBase(ChartView):
    chart_name = "velocity"
    form_class = forms.VelocityChartForm

    def get_context_data(self, board_id, **kwargs):
        board = Board.objects.by_id(board_id)
        today = timezone.now().date()
        self.initial_form_data["from_dt"] = today - datetime.timedelta(days=180)
        self.initial_form_data["to_dt"] = today

        context = super(VelocityChartBase, self).get_context_data(**kwargs)

        context["board"] = board
        return context

    def get_chart_data(self, context):
        if self.form.is_bound:
            last_n = self.form.cleaned_data["last_n"]
        else:
            last_n = self.form.fields["last_n"].initial
        sprints = Sprint.objects.for_board_last_n(context["board"], last_n)
        cc = KeyVal.objects.sprint_commitment_columns(context["board"]).value["columns"]
        return ChartExporter.velocity_chart_c3(sprints, cc)


class VelocityChartView(VelocityChartBase):
    template_name = "chart/velocity_chart.html"

    def get_context_data(self, board_id, **kwargs):
        logger.debug("display velocity chart")

        self.chart_data_url = reverse("velocity-chart-data", args=(board_id, ))

        context = super(VelocityChartView, self).get_context_data(board_id, **kwargs)

        context["breadcrumbs"] = Breadcrumbs.board_detail(context["board"]) + \
            [Breadcrumbs.text("Velocity chart")]
        context["sprint_data"] = self.get_chart_data(context)
        context["velocity_chart_description"] = VELOCITY_CHART_DESCRIPTION
        return context


class VelocityChartDataView(VelocityChartBase):
    def post(self, request, board_id, *args, **kwargs):
        logger.debug("get data for velocity chart")
        self.form_data = request.POST
        context = super(VelocityChartDataView, self).get_context_data(board_id, **kwargs)
        form = context["form"]

        if not form.is_valid():
            return self.respond_json_form_errors([form])

        data = self.get_chart_data(context)
        return JsonResponse({"data": data})


class ListDetailBase(ChartView):
    chart_name = "list_history"
    form_class = forms.ListDetailForm

    def get_context_data(self, list_id, **kwargs):
        li = List.objects.get(id=list_id)
        today = timezone.now().date()
        self.initial_form_data["from_dt"] = today - datetime.timedelta(days=60)
        self.initial_form_data["to_dt"] = today

        context = super(ListDetailBase, self).get_context_data(**kwargs)

        context["list"] = li
        return context


class ListDetailView(ListDetailBase):
    template_name = "list_detail.html"

    def get_context_data(self, list_id, **kwargs):
        logger.debug("list detail: %s", list_id)

        self.chart_data_url = reverse("list-history-chart-data", args=(list_id, ))

        context = super(ListDetailView, self).get_context_data(list_id, **kwargs)

        context["breadcrumbs"] = Breadcrumbs.board_detail(context["list"].latest_action.board) + \
            [Breadcrumbs.text("Column \"%s\"" % context["list"].name)]
        context["list_stats"] = ListStat.objects.for_list_in_range(
            context["list"], self.initial_form_data["from_dt"], self.initial_form_data["to_dt"])
        return context


class ListDetailDataView(ListDetailBase):
    def post(self, request, list_id, *args, **kwargs):
        logger.debug("get data for list history chart: %s", list_id)
        self.form_data = request.POST
        context = super(ListDetailDataView, self).get_context_data(list_id, **kwargs)
        form = context["form"]

        if not form.is_valid():
            return self.respond_json_form_errors([form])

        data = ChartExporter.list_history_chart_c3(context["list"],
                                                   form.cleaned_data["from_dt"],
                                                   form.cleaned_data["to_dt"])
        return JsonResponse({"data": data})


def board_detail(request, board_id):
    board = Board.objects.by_id(board_id)
    logger.debug("board detail %s", board)

    kv_displ_cols = KeyVal.objects.displayed_cols_in_board_detail(request.user, board)
    kv_com = KeyVal.objects.sprint_commitment_columns(board)

    if request.method == "POST":
        form_data = request.POST
    else:
        form_data = None

    lis = List.objects.get_all_listnames_for_board(board)

    columns_form = forms.ListsSelectorForm(
        kv_displ_cols.value["columns"],
        lis,
        data=form_data,
        prefix="col"
    )
    commitment_form = forms.ListsSelectorForm(
        kv_com.value["columns"],
        lis,
        data=form_data,
        prefix="com"
    )
    if request.method == "POST":
        if commitment_form.is_valid() and columns_form.is_valid():
            kv_displ_cols.value["columns"] = columns_form.workflow
            kv_displ_cols.save()
            kv_com.value["columns"] = commitment_form.workflow
            kv_com.save()
        else:
            logger.warning("formsets are not valid: %s %s", commitment_form, columns_form)
            # TODO: propagate to client

    lists = List.objects.filter_lists_for_board(board, f=kv_displ_cols.value["columns"])
    lists = sorted(lists, key=lambda x: x.name)

    sprints = Sprint.objects.filter(board__id=board_id).order_by("start_dt")
    context = {
        "board": board,
        "lists": lists,
        "sprints": sprints,
        "columns_form": columns_form,
        "commitment_form": commitment_form,
        "form_post_url": reverse("board-detail", args=(board_id, )),
        "errors": KeyVal.objects.board_messages(board).value["messages"],
        "breadcrumbs": [
            Breadcrumbs.url(reverse("index"), "Boards"),
            Breadcrumbs.text(board.name)
        ],
        "selected_columns_description": SELECTED_COLUMNS_DESCRIPTION,
        "sprint_commitment_description": SPRINT_COMMITMENT_DESCRIPTION,
        "data_synchronization_description": DATA_SYNCHRONIZATION_DESCRIPTION,
        "sprint_calculation_description": SPRINT_CALCULATION_DESCRIPTION,
    }
    return render(request, "board_detail.html", context)


def board_refresh(request, board_id):
    board = Board.objects.by_id(board_id)
    logger.debug("refresh board %s", board)
    board.ensure_actions(request.COOKIES["token"])
    return redirect('board-detail', board_id=board_id)


def sprint_create(request, board_id):
    board = Board.objects.by_id(board_id)
    logger.debug("sprint create for board: %s", board)

    if request.method == "POST":
        form = forms.SprintCreateForm(data=request.POST)
        form.instance.board = board
        logger.debug("user's timezone = %s", request.user.timezone)
        if form.is_valid():
            sprint = form.save()
            logger.debug("creating new sprint: %s", sprint)
            Sprint.set_completed_list(board)
            return redirect('sprint-detail', sprint_id=sprint.id)
    else:
        form = forms.SprintCreateForm()

    context = {
        "form": form,
        "post_url": reverse("sprint-create", args=(board_id, )),
        "breadcrumbs": Breadcrumbs.board_detail(board) +
                       [Breadcrumbs.text("Create sprint")]
    }
    return render(request, "sprint_create.html", context)


def sprint_detail(request, sprint_id):
    sprint = Sprint.objects.get(id=sprint_id)
    logger.debug("sprint detail: %s", sprint)
    # edit sprint as soon as possible
    if request.method == "POST":
        sprint_edit_form = forms.SprintEditForm(data=request.POST, instance=sprint)
        logger.debug("user's timezone = %s", request.user.timezone)
        if sprint_edit_form.is_valid():
            sprint = sprint_edit_form.save()
            logger.debug("saving updated sprint: %s", sprint)
    else:
        sprint_edit_form = forms.SprintEditForm(instance=sprint)

    sprint_cards = Card.objects.sprint_cards_with_latest_actions(sprint)
    sprint_card_ids = [x.id for x in sprint_cards]

    unfinished_cards = []
    if sprint.completed_list is not None:
        # don't supply date, we want latest stuff
        completed_card_actions = CardAction.objects.safe_card_actions_on_list_in(
            sprint.board,
            sprint.completed_list,
        )
        completed_card_ids = [x.card_id for x in completed_card_actions]
        unfinished_cards = [card for card in sprint_cards if card.id not in completed_card_ids]
    else:
        completed_card_actions = CardAction.objects.card_actions_on_list_names_in(
            sprint.board,
            COMPLETED_COLUMNS
        )

    current_sprint_cas = CardAction.objects.card_actions_on_list_names_in(
        sprint.board, ["Next", "In Progress", "Complete"], min(timezone.now(), sprint.end_dt))
    added_after_sprint_card_actions = [ca for ca in current_sprint_cas if ca.card_id not in sprint_card_ids]

    chart_url = reverse("burndown-chart-data", args=(sprint.board.id, ), )
    chart_url += "?" + urlencode({"sprint_id": sprint.id})

    context = {
        "form": sprint_edit_form,
        "post_url": reverse("sprint-detail", args=(sprint_id, )),
        "sprint": sprint,
        "sprint_cards": sprint_cards,
        "completed_card_actions": completed_card_actions,
        "unfinished_cards": unfinished_cards,
        "after_sprint_cas": added_after_sprint_card_actions,
        "view_name": "chart_without_form",
        "chart_name": "burndown",
        "chart_data_url": chart_url,
        "submit_input_type": "submit",
        "breadcrumbs": Breadcrumbs.board_detail(sprint.board) +
                       [Breadcrumbs.text("Sprint \"%s\"" % sprint.name)]
    }
    return render(request, "sprint_detail.html", context)


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
        "breadcrumbs": Breadcrumbs.board_detail(action_list[-1].board) +
                       [Breadcrumbs.text("Card \"%s\"" % display_card(action_list[-1]))]
    }
    return render(request, "card_detail.html", context)


def stalled_cards(request, list_id):
    li = List.objects.get(id=list_id)
    board = li.latest_action.board
    card_actions = CardAction.objects.safe_card_actions_on_list_in(board, li)
    card_actions = sorted(card_actions, key=lambda x: x.date)
    context = {
        "list": li,
        "card_actions": card_actions,
        "breadcrumbs": Breadcrumbs.board_detail(board) +
                       [Breadcrumbs.text("Stalled cards on \"%s\"" % li.name)]
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
