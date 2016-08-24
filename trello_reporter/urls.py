import logging

from django.conf.urls import url, include
from django.conf import settings
from django.contrib import admin

from trello_reporter.charting.urls import urlpatterns as charting_urls
from trello_reporter.authentication.urls import urlpatterns as auth_urls


logger = logging.getLogger(__name__)


urlpatterns = [
    url(r'^admin/', admin.site.urls),
]

urlpatterns += auth_urls
urlpatterns += charting_urls

if settings.DEBUG:
    try:
        import debug_toolbar
    except ImportError:
        logger.warning("Django debug toolbar is not installed")
        pass
    else:
        urlpatterns += [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ]
