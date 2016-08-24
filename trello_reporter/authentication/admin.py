from django.contrib import admin

from .models import TrelloUser


@admin.register(TrelloUser)
class UserAdmin(admin.ModelAdmin):
    list_display = ["trello_id", "username", "full_name"]
