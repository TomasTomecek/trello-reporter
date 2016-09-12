from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.shortcuts import render

from trello_reporter.authentication.forms import UserProfileForm
from trello_reporter.charting.views import logger, Breadcrumbs


def trello_redirect(request):
    return render(request, "trello_redirect.html")


def authenticate_with_token(request):
    logger.debug("redirect to index, user = %s", request.user)
    # TODO: redirect to request.GET["next"] or index
    response = {"redirect_to": reverse('index')}
    return JsonResponse(response)


def user_profile(request):
    logger.debug("user profile %s", request.user)
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
        logger.debug("form.errors = %s", form.errors)
    else:
        form = UserProfileForm(instance=request.user)
    context = {
        "form": form,
        "breadcrumbs": [
            Breadcrumbs.text("User profile \"%s\"" % request.user.full_name)
        ],
    }
    return render(request, "user_profile.html", context)
