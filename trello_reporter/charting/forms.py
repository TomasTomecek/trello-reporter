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


class Workflow(forms.Form):
    """
    State1   State2   State3   ...
    list   → list2  → list4
    ...      list3    ...
             ...
    """
    from_dt = forms.DateTimeField()
    to_dt = forms.DateTimeField()
    count = forms.FloatField()
    time_type = forms.ChoiceField(choices=DELTA_CHOICES)


class DateForm(forms.Form):
    date = forms.DateTimeField()


class RangeForm(forms.Form):
    from_dt = forms.DateTimeField(required=False)
    to_dt = forms.DateTimeField(required=False)


class BurndownForm(RangeForm):
    sprint = forms.ModelChoiceField(queryset=Sprint.objects.all(), required=False)

    def clean(self):
        cleaned_data = super(BurndownForm, self).clean()

        f = cleaned_data.get("from_dt")
        t = cleaned_data.get("to_dt")
        s = cleaned_data.get("sprint")

        if f and t and s:
            raise forms.ValidationError('Either pick sprint, or specify interval, not both')

        if not s and not (f and t):
            raise forms.ValidationError('Both "from" and "to" has to be filled.')


class ControlChartForm(BurndownForm):
    pass
