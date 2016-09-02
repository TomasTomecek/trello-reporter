# -*- coding: utf-8 -*-
"""
forms used for charts
"""

import logging

from django import forms

from trello_reporter.charting.models import Sprint

logger = logging.getLogger(__name__)

DELTA_CHOICES = (
    ("h", "Hour(s)"),
    ("d", "Day(s)"),
    ("m", "Month(s)"),
)


# MIXINS
# they have to derive from forms.Form, NOT from object (django metaclass magic)


class SelectWidgetWithCustomId(forms.Select):
    def render(self, name, value, attrs=None, **kwargs):
        attrs["id"] = "workflow-1"
        return super(SelectWidgetWithCustomId, self).render(name, value, attrs=attrs, **kwargs)


class ChoiceFieldWithCustomId(forms.ChoiceField):
    widget = SelectWidgetWithCustomId


# TODO: rewrite and use formsets
class WorkflowMixin(forms.Form):
    # initial workflow select, rest is spawned via javascript
    workflow = ChoiceFieldWithCustomId(
        required=False,  # we'll validate in our clean()
        label="Workflow"
    )

    def set_workflow_choices(self, values):
        self.fields["workflow"].choices = values

    def clean(self):
        cleaned_data = super(WorkflowMixin, self).clean()

        idx = 1
        cleaned_data["workflow"] = []
        while True:
            wf_key = "workflow-%d" % idx
            try:
                value = self.data[wf_key].strip()
            except KeyError:
                logger.info("workflow key %s not found", wf_key)
                break
            else:
                logger.debug("value = %s", value)
                idx += 1
                if not value:
                    continue
                cleaned_data["workflow"].append(value)
        if not cleaned_data["workflow"]:
            raise forms.ValidationError("Please select at least one value.")
        return cleaned_data


class DateInputWithDatepicker(forms.DateInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"]["class"] = "datepicker"
        super(DateInputWithDatepicker, self).__init__(*args, **kwargs)


class DateFieldWithDatepicker(forms.DateField):
    widget = DateInputWithDatepicker


class RangeMixin(forms.Form):
    from_dt = DateFieldWithDatepicker(label="From", required=False)
    to_dt = DateFieldWithDatepicker(label="To", required=False)

    def clean(self):
        cleaned_data = super(RangeMixin, self).clean()

        f = cleaned_data.get("from_dt")
        t = cleaned_data.get("to_dt")

        if not (f or t):
            raise forms.ValidationError('Please specify "From" or "To".')

        return cleaned_data


class SprintMixin(forms.Form):
    sprint = forms.ModelChoiceField(queryset=Sprint.objects.none(), required=False, label="Sprint")

    def set_sprint_choices(self, queryset):
        self.fields["sprint"].queryset = queryset


class SprintAndRangeMixin(SprintMixin, RangeMixin):
    def clean(self):
        cleaned_data = super(SprintAndRangeMixin, self).clean()

        f = cleaned_data.get("from_dt")
        s = cleaned_data.get("sprint")

        if f and s:
            raise forms.ValidationError('Either pick sprint, or specify interval, not both.')

        if not (s or f):
            raise forms.ValidationError(
                'Either sprint or beginning of a date range needs to specified.')

        return cleaned_data


class DeltaMixin(forms.Form):
    """
    e.g. delta = 3h, 1d, 2m, ...
    """
    count = forms.FloatField(label="Delta size")
    time_type = forms.ChoiceField(choices=DELTA_CHOICES, label="Delta unit")


class DateForm(forms.Form):
    date = DateFieldWithDatepicker(label="Date")


# ACTUAL FORMS


class ControlChartForm(WorkflowMixin, SprintAndRangeMixin, DeltaMixin, forms.Form):
    def clean(self):
        cleaned_data = WorkflowMixin.clean(self)
        cleaned_data.update(SprintAndRangeMixin.clean(self))
        return cleaned_data


class BurndownForm(SprintAndRangeMixin, forms.Form):
    pass
