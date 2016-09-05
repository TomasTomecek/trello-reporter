# -*- coding: utf-8 -*-
"""
forms used for charts
"""

import logging

import datetime
from django import forms

from trello_reporter.charting.models import Sprint

logger = logging.getLogger(__name__)

TICK_CHOICES = (
    ("h", "Hour(s)"),
    ("d", "Day(s)"),
    ("m", "Month(s)"),
)


# MIXINS
# they have to derive from forms.Form, NOT from object (django metaclass magic)


class WorkflowMixin(forms.Form):
    # initial workflow select, rest is spawned via javascript
    workflow = forms.ChoiceField(
        required=False,  # we'll validate in our clean()
        label="Workflow",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    def set_initial_data(self, value):
        self.fields["workflow"].initial = value

    def set_workflow_choices(self, values):
        self.fields["workflow"].choices = values


class WorkflowBaseFormSet(forms.BaseFormSet):
    def set_initial_data(self, values):
        [form.set_initial_data(values[idx]) for idx, form in enumerate(self.forms)]

    def set_choices(self, choices):
        [form.set_workflow_choices(choices) for form in self.forms]

    @property
    def workflow(self):
        if not self.is_valid():
            logger.warning("formset is invalid")
            raise Exception("form is invalid")
        response = []
        for form in self.forms:
            try:
                response.append(form.cleaned_data.values()[0])
            except IndexError:
                # might not be filled
                continue
        return response

    def clean(self):
        if not self.workflow:
            raise forms.ValidationError("Please select at least one value.")


def get_workflow_formset(choices, initial_data, data=None):
    fs_kls = forms.formset_factory(
        WorkflowMixin, formset=WorkflowBaseFormSet)
    fs = fs_kls(data=data, initial=[{"workflow": x} for x in initial_data])
    fs.set_choices(choices)
    return fs


class DateInputWithDatepicker(forms.DateInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"]["class"] = "datepicker form-control"
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
    sprint = forms.ModelChoiceField(queryset=Sprint.objects.none(), required=False, label="Sprint",
                                    widget=forms.Select(attrs={"class": "form-control"}))

    def set_sprint_choices(self, queryset):
        self.fields["sprint"].queryset = queryset


class SprintAndRangeMixin(SprintMixin, RangeMixin):
    def clean(self):
        cleaned_data = super(forms.Form, self).clean()  # don't call range's clean()

        f = cleaned_data.get("from_dt")
        s = cleaned_data.get("sprint")

        if f and s:
            raise forms.ValidationError('Either pick sprint, or specify interval, not both.')

        if not (s or f):
            raise forms.ValidationError(
                'Either sprint or beginning of a date range needs to specified.')

        if s:
            cleaned_data["beginning"] = s.start_dt
            cleaned_data["end"] = s.end_dt
        else:
            cleaned_data["beginning"] = cleaned_data["from_dt"]
            cleaned_data["end"] = cleaned_data["to_dt"]

        return cleaned_data


class DeltaMixin(forms.Form):
    """
    e.g. delta = 3h, 1d, 2m, ...
    """
    count = forms.IntegerField(label="Tick size",
                               widget=forms.NumberInput(attrs={"class": "form-control"}))
    time_type = forms.ChoiceField(choices=TICK_CHOICES, label="Tick unit",
                                  widget=forms.Select(attrs={"class": "form-control"}))

    def clean(self):
        cleaned_data = super(forms.Form, self).clean()
        count = cleaned_data["count"]
        time_type = cleaned_data["time_type"]

        if time_type == "d":
            delta = datetime.timedelta(days=count)
        elif time_type == "m":
            delta = datetime.timedelta(days=count * 30)
        elif time_type == "h":
            delta = datetime.timedelta(seconds=count * 3600)
        else:
            raise forms.ValidationError("Invalid time measure.")
        cleaned_data["delta"] = delta
        return cleaned_data


class DateForm(forms.Form):
    date = DateFieldWithDatepicker(label="Date")


# ACTUAL FORMS


class ControlChartForm(SprintAndRangeMixin):
    pass


class BurndownChartForm(SprintAndRangeMixin):
    pass


class CumulativeFlowChartForm(SprintAndRangeMixin, DeltaMixin):
    def clean(self):
        d = SprintAndRangeMixin.clean(self)
        d.update(DeltaMixin.clean(self))
        return d


class VelocityChartForm(RangeMixin):
    pass