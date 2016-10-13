from __future__ import unicode_literals

import copy

from django.db import models
from django.contrib.postgres.fields import JSONField


def graceful_chain_get(d, *args):
    if not d:
        return None
    t = copy.deepcopy(d)
    for arg in args:
        try:
            t = t[arg]
        except (IndexError, KeyError):
            return None
    return t


class CardActionEventQuerySet(models.QuerySet):
    def for_card(self, trello_card_id):
        return self.filter(data__data__card__id=trello_card_id)


class CardActionEventManager(models.Manager):
    def card_names(self, trello_card_id):
        """ return list of names the card had for its lifetime """
        return set([x.data["data"]["card"]["name"]
                    for x in self.for_card_by_date(trello_card_id)])

    def for_card_by_date(self, trello_card_id):
        # we can't order by date b/c of some nonsense; should be ordered anyway
        return self.for_card(trello_card_id)


class CardActionEvent(models.Model):
    """ 1:1 mapping between events sent by trello """

    # complete response from trello API
    #
    # [{u'data': {u'board': {u'id': u'5783a02a78cd8946ec84572a',
    #                        u'name': u'Trello Reports',
    #                        u'shortLink': u'S4m1yrfb'},
    #             u'card': {u'id': u'5783b90cea9ad4c54ce998ff',
    #                       u'idList': u'5784d533c273958ad9c1a895',
    #                       u'idShort': 19,
    #                       u'name': u'Control chart',
    #                       u'shortLink': u'wHX1jFVZ'},
    #             u'listAfter': {u'id': u'5784d533c273958ad9c1a895',
    #                            u'name': u'Blocked'},
    #             u'listBefore': {u'id': u'5783a02a78cd8946ec84572d',
    #                             u'name': u'Next'},
    #             u'old': {u'idList': u'5783a02a78cd8946ec84572d'}},
    #   u'date': u'2016-07-12T11:32:14.696Z',
    #   u'id': u'5784d53e6238494254e0c964',
    #   u'idMemberCreator': u'54647c122edb0742214c751c',
    #   u'memberCreator': {u'avatarHash': u'b7f6d38057d04b49609572f7fea7d203',
    #                      u'fullName': u'Tomas Tomecek',
    #                      u'id': u'54647c122edb0742214c751c',
    #                      u'initials': u'TT',
    #                      u'username': u'tomastomecek1'},
    #   u'type': u'updateCard'},
    data = JSONField()
    processed_well = models.BooleanField(default=False)  # = is there an equal CardAction?

    objects = CardActionEventManager.from_queryset(CardActionEventQuerySet)()

    @property
    def card_name(self):
        return graceful_chain_get(self.data, "data", "card", "name")

    @property
    def card_id(self):
        return graceful_chain_get(self.data, "data", "card", "id")

    @property
    def list_name(self):
        return graceful_chain_get(self.data, "data", "list", "name")

    @property
    def card_short_id(self):
        return graceful_chain_get(self.data, "data", "card", "idShort")

    @property
    def card_url(self):
        u = graceful_chain_get(self.data, "data", "card", "id")
        if u:
            return "https://trello.com/c/%s" % u
