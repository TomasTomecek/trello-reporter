from django.conf.urls import url
from django.contrib import admin

from trello_reporter.charting.urls import urlpatterns as charting_urls
from trello_reporter.authentication.urls import urlpatterns as auth_urls


urlpatterns = [
    url(r'^admin/', admin.site.urls),
]

urlpatterns += auth_urls
urlpatterns += charting_urls
