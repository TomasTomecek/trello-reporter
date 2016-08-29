# -*- coding: utf-8 -*-
"""
TODO:
 * do inheritance for DRY
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


class DateInputWithDatepicker(forms.DateInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"]["class"] = "datepicker"
        super(DateInputWithDatepicker, self).__init__(*args, **kwargs)


class DateFieldWithDatepicker(forms.DateField):
    widget = DateInputWithDatepicker


class RangeForm(forms.Form):
    from_dt = DateFieldWithDatepicker(label="From", required=False)
    to_dt = DateFieldWithDatepicker(label="To", required=False)

    def clean(self):
        cleaned_data = super(RangeForm, self).clean()

        f = cleaned_data.get("from_dt")
        t = cleaned_data.get("to_dt")

        if not (f or t):
            raise forms.ValidationError('Please specify "From" or "To".')

        return cleaned_data


class Workflow(RangeForm):
    """
    State1   State2   State3   ...
    list   → list2  → list4
    ...      list3    ...
             ...
    """
    count = forms.FloatField(label="Delta size")
    time_type = forms.ChoiceField(choices=DELTA_CHOICES, label="Delta unit")


class DateForm(forms.Form):
    date = DateFieldWithDatepicker(label="Date")


class BurndownForm(RangeForm):
    sprint = forms.ModelChoiceField(queryset=Sprint.objects.all(), required=False, label="Sprint")

    def clean(self):
        cleaned_data = super(BurndownForm, self).clean()

        f = cleaned_data.get("from_dt")
        t = cleaned_data.get("to_dt")
        s = cleaned_data.get("sprint")

        if f and t and s:
            raise forms.ValidationError('Either pick sprint, or specify interval, not both.')

        if not s and not f:
            raise forms.ValidationError('Either sprint or beginning of a date range needs to specified.')

        return cleaned_data


class ControlChartForm(BurndownForm):
    pass
