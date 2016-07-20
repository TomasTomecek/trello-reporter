"""trello_reporter URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from .charting import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^chart/(?P<board_id>[0-9]+)/$', views.chart, name='chart'),
    url(r'^chart/(?P<board_id>[0-9]+)/cards_at/$', views.cards_on_board_at, name='cards-at'),
    url(r'^chart/(?P<board_id>[0-9]+)/cumulative/$', views.cumulative_chart,
        name='cumulative-chart'),
    url(r'^$', views.index, name='index'),
]
