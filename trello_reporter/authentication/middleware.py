"""
authenticating users with trello
"""
import os
import logging
from urllib import urlencode

import datetime
from django.contrib.auth import authenticate, login
from django.http.response import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings


url = "https://trello.com/1/authorize"
logger = logging.getLogger(__name__)


def form_authorize_url(redirect_url):
    options = {
        "key": os.environ["API_KEY"],
        "name": "Trello Reporter",
        "expiration": "never",
        "scope": "read",
        # postMessage - trello sends POST to the app
        # fragment - trello redirects with #token=asdqwe123456
        "callback_method": "fragment",
        "return_url": redirect_url,
    }
    return url + "?" + urlencode(options)


class TrelloAuthMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.
        self.redirect_url = reverse("auth-redirect")
        self.ignore_list = ["/api/v0/authenticate/", self.redirect_url]

    def __call__(self, request):
        token = None
        if "token" in request.GET:
            logger.info("token received")
            token_chain = request.GET.get("token", None)
            if token_chain is not None:
                token = token_chain.split("=", 1)[1]
                logger.debug("token = %s", token)
                user = authenticate(token=token)
                logger.info("user authenticated: %s", user)
                request.user = user
                login(request, user)
                logger.info("user logged in: %s", user)
        if request.user.is_authenticated and "token" in request.COOKIES:
            logger.info("user %s is authenticated", request.user)
            response = self.get_response(request)
        elif request.path in self.ignore_list:
            logger.debug("this endpoint ignores required authentication")
            response = self.get_response(request)
        else:
            # TODO: set "?next=<current_url>"
            full_path = request.build_absolute_uri(self.redirect_url)
            redirect_url = form_authorize_url(full_path)
            logger.info("redirect to trello authorization")
            return HttpResponseRedirect(redirect_url)
        if token:
            # in 30 days
            logger.debug("setting token cookie")
            expires = datetime.datetime.utcnow() + datetime.timedelta(days=30)
            response.set_cookie("token", token, expires=expires, secure=not settings.DEBUG)
            logger.debug(response.cookies)

        return response
