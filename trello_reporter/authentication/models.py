from __future__ import unicode_literals

import pytz

from django.contrib.postgres.fields.jsonb import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from trello_reporter.charting.constants import INITIAL_COLUMNS, SPRINT_COMMITMENT_COLUMNS


class TrelloUser(models.Model):
    """ contains data about trello users """
    username = models.CharField(max_length=255, db_index=True, unique=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    trello_id = models.CharField(max_length=32, db_index=True)
    timezone = models.CharField(max_length=63,
                                choices=zip(pytz.common_timezones, pytz.common_timezones),
                                default="UTC")
    # we DO NOT store user's token persistently, ever

    last_login = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)  # FIXME: in prod

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["trello_id"]

    def __unicode__(self):
        return "%s (%s)" % (self.username, self.full_name)

    # User API

    @property
    def is_anonymous(self):
        """
        Always return False. This is a way of comparing User objects to
        anonymous users.
        """
        return False

    @property
    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return True

    def has_module_perms(self, app_label):
        return True

    def has_perm(self, perm):
        return True

    @classmethod
    def get_or_create(cls, trello_id, username, full_name=None):
        obj, created = cls.objects.get_or_create(trello_id=trello_id, username=username)
        if full_name and obj.full_name != full_name:
            obj.full_name = full_name
        obj.save()
        return obj


class KeyValQuerySet(models.QuerySet):
    def for_key(self, key):
        return self.filter(key=key)

    def for_user(self, user_id):
        return self.filter(value__user_id=user_id)

    def for_board(self, board_id):
        return self.filter(value__board_id=board_id)

    def get_or_create_setting(self, key, user_id=None, board_id=None, default=None):
        q = {"key": key}
        if user_id:
            q["value__user_id"] = user_id
        if board_id:
            q["value__board_id"] = board_id
        try:
            return self.get(**q)
        except ObjectDoesNotExist:
            value = {}
            if board_id:
                value["user_id"] = user_id
            if board_id:
                value["board_id"] = board_id
            if default:
                value.update(default)
            return self.create(key=key, value=value)


class KeyValManager(models.Manager):
    def displayed_cols_in_board_detail(self, user, board):
        return self.get_or_create_setting(
            KeyVal.DISPLAYED_COLS_IN_BOARD_DETAIL, user_id=user.id, board_id=board.id,
            default={"columns": INITIAL_COLUMNS}
        )

    def sprint_commitment_columns(self, board):
        return self.get_or_create_setting(
            KeyVal.SPRINT_COMMITMENT_COLS, board_id=board.id,
            default={"columns": SPRINT_COMMITMENT_COLUMNS}
        )

    def board_messages(self, board):
        """
        {
            "messages": [
                {"message": "..."}
            ]
        }
        :param board:
        :return:
        """
        return self.get_or_create_setting(
            KeyVal.BOARD_MESSAGES, board_id=board.id,
            default={"messages": []}
        )


class KeyVal(models.Model):
    """ key & value table """
    key = models.CharField(max_length=63, db_index=True)
    value = JSONField()

    objects = KeyValManager.from_queryset(KeyValQuerySet)()

    def __unicode__(self):
        return "%s: %s" % (self.key, self.value)

    DISPLAYED_COLS_IN_BOARD_DETAIL = "DISPLAYED_COLS_IN_BOARD_DETAIL"
    SPRINT_COMMITMENT_COLS = "SPRINT_COMMITMENT_COLS"
    BOARD_MESSAGES = "BOARD_MESSAGES"
