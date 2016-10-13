from __future__ import unicode_literals

import datetime
import pytest
from pytz import timezone as pytz_timezone
from flexmock import flexmock
from django.utils import timezone

from trello_reporter.charting.forms import ControlChartForm, get_workflow_formset, \
    datetime_in_current_timezone
from trello_reporter.charting.models import Sprint, Board


def test_workflow_formset_render():
    choices = [("A", "A"), ("B", "B")]
    f = get_workflow_formset(choices, [])
    html = f.as_ul()
    assert "<option value=\"A\">A</option>" in html
    assert "<option value=\"B\">B</option>" in html


def test_workflow_formset_initial_data():
    choices = [("A", "A"), ("B", "B")]
    initial_data = ["A"]
    f = get_workflow_formset(choices, initial_data)
    assert f.forms[0].fields["workflow"].choices == choices
    html = f.as_ul()
    assert "<option value=\"A\" selected=\"selected\">A</option>" in html


def test_workflow_formset_data():
    choices = [("A", "A"), ("B", "B")]
    f = get_workflow_formset(choices, [], data={
        'form-TOTAL_FORMS': '3',
        'form-INITIAL_FORMS': '2',
        'form-MAX_NUM_FORMS': '',
        'form-0-workflow': 'A',
        'form-1-workflow': 'B',
        'form-2-workflow': '',
    })
    assert f.is_valid()
    assert f.total_error_count() == 0
    assert f.workflow == ["A", "B"]


def test_control_form_has_fields():
    f = ControlChartForm()
    assert len(f.fields) == 3  # start_dt, end_dt, sprint


@pytest.mark.django_db
def test_control_form_can_be_rendered():
    b = Board.get_or_create_board("1", name="B")
    Sprint.objects.bulk_create([
        Sprint(name="S 1", sprint_number=1, board=b),
        Sprint(name="S 2", sprint_number=2, board=b),
        Sprint(name="S 3", sprint_number=3, board=b),
        Sprint(name="S 4", sprint_number=4, board=b),
    ])
    f = ControlChartForm()
    f.set_sprint_choices(Sprint.objects.all())
    assert f.as_ul()


def test_datetime_in_current_timezone():
    tz = pytz_timezone("Europe/Bratislava")
    flexmock(timezone, get_current_timezone=lambda: tz)

    date = datetime.date(2016, 1, 1)
    time = datetime.time(10, 0, 0)

    dt = datetime_in_current_timezone(date, time)
    fmt = '%Y-%m-%d %H:%M:%S %Z%z'
    assert dt.strftime(fmt) == "2016-01-01 10:00:00 CET+0100"
