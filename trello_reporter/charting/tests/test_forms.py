from __future__ import unicode_literals

import pytest

from trello_reporter.charting.forms import ControlChartForm, WorkflowFormSet
from trello_reporter.charting.models import Sprint, Board


# @pytest.mark.django_db
# def test_workflow_clean():
#     List.objects.bulk_create([
#         List(trello_id="1", name="A"),
#         List(trello_id="2", name="B"),
#         List(trello_id="3", name="C"),
#         List(trello_id="4", name="D"),
#     ])
#     f = WorkflowMixin({"workflow-1": "B", "workflow-2": "C"})
#     assert f.is_valid(), f.errors
#     assert f.cleaned_data == {"workflow": ["B", "C"]}


def test_workflow_formset_render():
    f = WorkflowFormSet()
    f.set_choices([("A", "A"), ("B", "B")])
    html = f.as_ul()
    assert "<option value=\"A\">A</option>" in html
    assert "<option value=\"B\">B</option>" in html


def test_workflow_formset_initial_data():
    f = WorkflowFormSet()
    choices = [("A", "A"), ("B", "B")]
    f.set_choices(choices)
    f.set_initial_data(["A"])
    assert f.forms[0].fields["workflow"].choices == choices
    assert f.forms[0].fields["workflow"].initial == "A"
    html = f.as_ul()
    assert "<option value=\"A\" selected=\"selected\">A</option>" in html


def test_workflow_formset_data():
    f = WorkflowFormSet({
        'form-TOTAL_FORMS': '3',
        'form-INITIAL_FORMS': '2',
        'form-MAX_NUM_FORMS': '',
        'form-0-workflow': 'A',
        'form-1-workflow': 'B',
    })
    f.set_choices([("A", "A"), ("B", "B")])
    assert f.is_valid()
    assert f.total_error_count() == 0
    assert f.workflow == ["A", "B"]


def test_control_form_has_fields():
    f = ControlChartForm()
    assert len(f.fields) == 5


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
