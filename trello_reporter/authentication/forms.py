from django import forms

from trello_reporter.authentication.models import TrelloUser


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = TrelloUser
        fields = ['timezone']
        widgets = {
            "timezone": forms.Select(attrs={"class": "form-control"})
        }
