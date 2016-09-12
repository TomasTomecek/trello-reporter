import pytest

from django.core.urlresolvers import reverse
from django.utils import timezone

from trello_reporter.charting.models import Board, Sprint, List, CardAction, Card
from trello_reporter.charting.views import ControlChartDataView, ControlChartView
from trello_reporter.harvesting.models import CardActionEvent


@pytest.mark.django_db
def test_control_chart(rf):
    b = Board.get_or_create_board("1", name="B")
    Sprint.objects.bulk_create([
        Sprint(name="S 1", sprint_number=1, board=b),
    ])
    request = rf.get(reverse("show-control-chart", args=(b.id, )))
    response = ControlChartView.as_view()(request, board_id=b.id)
    assert response.status_code == 200


@pytest.mark.django_db
def test_control_chart_data(rf):
    b = Board.get_or_create_board("1", name="B")
    li = List.get_or_create_list("2", "Next")
    sp = Sprint.objects.create(name="S 1", sprint_number=1, board=b)
    c = Card.objects.create(trello_id="4", name="Card name")
    ev = CardActionEvent.objects.create(data={}, processed_well=True)
    ca = CardAction.objects.create(
        trello_id="3",
        date=timezone.now(),
        action_type="createCard",
        card=c,
        event=ev,
        board=b,
        list=li,
    )
    request = rf.post(reverse("control-chart-data", args=(b.id, )), data={
        'form-TOTAL_FORMS': '1',
        'form-INITIAL_FORMS': '1',
        'form-MAX_NUM_FORMS': '',
        'form-0-workflow': 'Next',
    })
    c = ControlChartDataView()
    response = c.post(request, board_id=b.id)
    assert response.status_code == 200
