from __future__ import unicode_literals

from django.db import models


class TrelloUser(models.Model):
    """ contains data about trello users """
    username = models.CharField(max_length=255, db_index=True, unique=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    trello_id = models.CharField(max_length=32, db_index=True)
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
