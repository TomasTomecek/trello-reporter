from django.contrib import admin

from trello_reporter.charting.models import Board, CardAction, Card


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    pass


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    pass


@admin.register(CardAction)
class CardActionAdmin(admin.ModelAdmin):
    pass
