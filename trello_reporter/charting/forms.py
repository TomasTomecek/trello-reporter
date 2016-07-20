# -*- coding: utf-8 -*-

import logging

from django import forms


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
