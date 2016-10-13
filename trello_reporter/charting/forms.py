# -*- coding: utf-8 -*-
"""
forms used for charts
"""

import logging
import datetime

import pytz

from django import forms
from django.utils import timezone

from trello_reporter.charting.models import Sprint


logger = logging.getLogger(__name__)

TICK_CHOICES = (
    ("h", "Hour(s)"),
    ("d", "Day(s)"),
    ("m", "Month(s)"),
)
TIME_FORMAT = "%I:%M %p"

CARDS_FORM_ID = "c"
STORY_POINTS_FORM_ID = "sp"
CARDS_OR_SP_CHOICES = (
    (CARDS_FORM_ID, "Cards count"),
    (STORY_POINTS_FORM_ID, "Story points"),
)


# UTILS


def datetime_in_utc(date, time):
    if not date:
        return
    dt = datetime.datetime.combine(date, time)
    dt = pytz.utc.localize(dt)
    logger.debug("utc dt = %s", dt)
    return dt


def max_time_for_date(date):
    return datetime_in_utc(date, datetime.datetime.max.time())


def min_time_for_date(date):
    return datetime_in_utc(date, datetime.datetime.min.time())


def datetime_in_current_timezone(date, time):
    tz = timezone.get_current_timezone()
    logger.debug("current timezone = %s", tz)
    dt = datetime.datetime.combine(date, time)
    dt = tz.localize(dt)
    local_dt = tz.normalize(dt)
    logger.debug("tz-aware: %s local: %s", dt, local_dt)
    return local_dt


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
    def __init__(self, **kwargs):
        label = kwargs.pop("label", None)
        super(WorkflowBaseFormSet, self).__init__(**kwargs)
        if label:
            for idx, val in enumerate(self):
                self[idx].fields['workflow'].label = label

    def set_initial_data(self, values):
        [form.set_initial_data(values[idx]) for idx, form in enumerate(self.forms)]

    def set_choices(self, choices):
        [form.set_workflow_choices(choices) for form in self.forms]

    @property
    def workflow(self):
        if not self.is_valid():
            logger.warning("formset is invalid")
            raise forms.ValidationError("form is invalid")
        response = []
        for form in self.forms:
            try:
                response.append(form.cleaned_data.values()[0])
            except IndexError:
                # might not be filled
                continue
        return filter(None, response)

    def clean(self):
        if not self.workflow:
            raise forms.ValidationError("Please select at least one value.")


def get_workflow_formset(choices, initial_data, data=None, label=None, prefix=None):
    fs_kls = forms.formset_factory(
        WorkflowMixin, formset=WorkflowBaseFormSet)
    q = {
       "data": data,
       "initial": [{"workflow": x} for x in initial_data]
    }
    if label:
        q["label"] = label
    if prefix:
        q["prefix"] = prefix
    fs = fs_kls(**q)
    fs.set_choices(choices)
    return fs


class DateInputWithDatepicker(forms.DateInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"]["class"] = "datepicker form-control"
        super(DateInputWithDatepicker, self).__init__(*args, **kwargs)


class TimeInputWithDatepicker(forms.TimeInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"]["class"] = "timepicker form-control"
        kwargs["format"] = TIME_FORMAT
        super(TimeInputWithDatepicker, self).__init__(*args, **kwargs)


class DateFieldWithDatepicker(forms.DateField):
    widget = DateInputWithDatepicker


class TimeFieldWithDatepicker(forms.TimeField):
    widget = TimeInputWithDatepicker
    input_formats = [TIME_FORMAT]


class RangeForm(forms.Form):
    from_dt = DateFieldWithDatepicker(label="From", required=False)
    to_dt = DateFieldWithDatepicker(label="To", required=False)

    def clean(self):
        cleaned_data = super(RangeForm, self).clean()

        cleaned_data["from_dt"] = min_time_for_date(cleaned_data.get("from_dt"))
        cleaned_data["to_dt"] = max_time_for_date(cleaned_data.get("to_dt"))

        return cleaned_data


class SprintMixin(forms.Form):
    sprint = forms.ModelChoiceField(queryset=Sprint.objects.none(), required=False, label="Sprint",
                                    widget=forms.Select(attrs={"class": "form-control"}))

    def set_sprint_choices(self, queryset):
        self.fields["sprint"].queryset = queryset


class SprintAndRangeForm(SprintMixin, RangeForm):
    def clean(self):
        cleaned_data = SprintMixin.clean(self)
        cleaned_data.update(RangeForm.clean(self))

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


class RangeMixin(object):
    def clean(self):
        cleaned_data = super(RangeMixin, self).clean()

        f = cleaned_data.get("from_dt")
        t = cleaned_data.get("to_dt")

        if not (f or t):
            raise forms.ValidationError('Please specify "From" or "To".')

        return cleaned_data


class SprintPicker(forms.Form):
    last_n = forms.IntegerField(min_value=1, label="Latest n sprints", initial=5)


class CardsCountStoryPointsKnobMixin(forms.Form):
    cards_or_sp = forms.ChoiceField(choices=CARDS_OR_SP_CHOICES, label="Cumulative unit",
                                    initial=CARDS_FORM_ID)


# ACTUAL FORMS


class ControlChartForm(SprintAndRangeForm):
    pass


class BurndownChartForm(SprintAndRangeForm):
    pass


class CumulativeFlowChartForm(SprintAndRangeForm, DeltaMixin, CardsCountStoryPointsKnobMixin):
    def clean(self):
        d = SprintAndRangeForm.clean(self)
        d.update(DeltaMixin.clean(self))
        return d


class VelocityChartForm(SprintPicker):
    pass


class SprintBaseForm(forms.ModelForm):
    start_t = TimeFieldWithDatepicker()
    end_t = TimeFieldWithDatepicker()

    class Meta:
        model = Sprint
        fields = ['start_dt', 'end_dt', 'name', 'sprint_number']
        widgets = {
            "start_dt": DateInputWithDatepicker(),
            "end_dt": DateInputWithDatepicker(),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "sprint_number": forms.NumberInput(attrs={"class": "form-control"}),
        }
        labels = {
            "start_dt": "Start date",
            "end_dt": "End date"
        }

    def save(self, commit=True):
        self.instance.start_dt = datetime_in_current_timezone(
            self.cleaned_data["start_dt"], self.cleaned_data["start_t"])
        self.instance.end_dt = datetime_in_current_timezone(
            self.cleaned_data["end_dt"], self.cleaned_data["end_t"])
        self.instance.name = self.cleaned_data["name"]
        self.instance.sprint_number = self.cleaned_data["sprint_number"]
        super(SprintBaseForm, self).save(commit=commit)
        return self.instance


class SprintEditForm(SprintBaseForm):
    def __init__(self, *args, **kwargs):
        super(SprintEditForm, self).__init__(*args, **kwargs)
        tz = timezone.get_current_timezone()
        s = tz.normalize(self.instance.start_dt)
        e = tz.normalize(self.instance.end_dt)
        self.fields["start_t"].initial = s
        self.fields["end_t"].initial = e


class SprintCreateForm(SprintBaseForm):
    pass


class BoardDetailForm(forms.Form):
    pass


class ListDetailForm(RangeMixin, RangeForm):
    pass
