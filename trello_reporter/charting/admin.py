from django.contrib import admin

from trello_reporter.charting.models import Board, CardAction, Card, List


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    pass


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    pass


@admin.register(List)
class ListAdmin(admin.ModelAdmin):
    list_display = ["trello_id", "name"]


@admin.register(CardAction)
class CardActionAdmin(admin.ModelAdmin):
    list_display = ["trello_id", "date", "action_type", "card", "board"]
