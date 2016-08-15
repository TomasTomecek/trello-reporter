from django.contrib import admin

from trello_reporter.charting.models import Board, CardAction, Card, List, Sprint, ListStat


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ["trello_id", "name"]


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ["trello_id", "name"]


@admin.register(List)
class ListAdmin(admin.ModelAdmin):
    list_display = ["trello_id", "name"]


@admin.register(CardAction)
class CardActionAdmin(admin.ModelAdmin):
    list_display = ["trello_id", "date", "action_type", "card", "board"]


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ["id", "start_dt", "end_dt", "board"]


@admin.register(ListStat)
class ListStatAdmin(admin.ModelAdmin):
    list_display = ["id", "card_action", "diff", "cards_rt", "story_points_rt"]
