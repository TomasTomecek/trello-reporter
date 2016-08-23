from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.shortcuts import render

from trello_reporter.charting.views import logger


def trello_redirect(request):
    return render(request, "trello_redirect.html")


def authenticate_with_token(request):
    logger.debug("redirect to index, user = %s", request.user)
    # TODO: redirect to request.GET["next"] or index
    response = {"redirect_to": reverse('index')}
    return JsonResponse(response)