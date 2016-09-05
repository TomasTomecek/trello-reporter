import pytest

from django.core.urlresolvers import reverse

from trello_reporter.charting.models import Board, Sprint
from trello_reporter.charting.views import ControlChartDataView, ControlChartView


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
    Sprint.objects.bulk_create([
        Sprint(name="S 1", sprint_number=1, board=b),
    ])
    request = rf.get(reverse("control-chart-data", args=(b.id, )))
    response = ControlChartDataView.as_view()(request, board_id=b.id)
    assert response.status_code == 200
