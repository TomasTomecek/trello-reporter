import logging

from django.core.exceptions import ObjectDoesNotExist

from trello_reporter.authentication.models import TrelloUser
from trello_reporter.charting.harvesting import Harvestor


logger = logging.getLogger(__name__)


class TrelloAuthBackend(object):
    def get_user(self, pk):
        try:
            return TrelloUser.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return None

    def authenticate(self, token):
        member_info = Harvestor.get_member_info_by_token(token)

        username = member_info["username"]
        full_name = member_info["fullName"]
        trello_id = member_info["id"]

        user = TrelloUser.get_or_create(trello_id, username, full_name=full_name)

        return user
