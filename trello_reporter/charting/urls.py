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

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^board/(?P<board_id>[0-9]+)/$', views.board_detail, name='board-detail'),
    url(r'^board/(?P<board_id>[0-9]+)/refresh/$', views.board_refresh, name='board-refresh'),

    url(r'^column/(?P<list_id>[0-9]+)/$',
        views.list_detail, name='list-detail'),
    url(r'^column/(?P<list_id>[0-9]+)/stalled-cards/$',
        views.stalled_cards, name='stalled-cards'),
    url(r'^card/(?P<card_id>[0-9]+)/$',
        views.card_detail, name='card-detail'),
    url(r'^sprint/(?P<sprint_id>[0-9]+)/$',
        views.sprint_detail, name='sprint-detail'),

    url(r'^board/(?P<board_id>[0-9]+)/cards-at/$', views.cards_on_board_at, name='cards-at'),
    url(r'^board/(?P<board_id>[0-9]+)/card-history/$', views.card_history, name='card-history'),
    url(r'^board/(?P<board_id>[0-9]+)/cumulative/$', views.show_cumulative_chart,
        name='show-cumulative-chart'),
    url(r'^board/(?P<board_id>[0-9]+)/control/$', views.ControlChartView.as_view(),
        name='show-control-chart'),
    url(r'^board/(?P<board_id>[0-9]+)/velocity/$', views.show_velocity_chart,
        name='show-velocity-chart'),
    url(r'^board/(?P<board_id>[0-9]+)/burndown/$', views.show_burndown_chart,
        name='show-burndown-chart'),

    url(r'^api/v0/card/(?P<card_id>[0-9]+)/$', views.api_get_card, name='api-get-card'),
    url(r'^api/v0/board/(?P<board_id>[0-9]+)/cumulative-flow/$', views.cumulative_chart_data,
        name='cumulative-chart-data'),
    url(r'^api/v0/board/(?P<board_id>[0-9]+)/control/$', views.ControlChartDataView.as_view(),
        name='control-chart-data'),
    url(r'^api/v0/column/(?P<list_id>[0-9]+)/list-history/$', views.list_history_data,
        name='list-history-chart-data'),
    url(r'^api/v0/board/(?P<board_id>[0-9]+)/burndown/$',
        views.burndown_chart_data,
        name='burndown-chart-data'),
    url(r'^api/v0/board/(?P<board_id>[0-9]+)/velocity/$', views.velocity_chart_data,
        name='velocity-chart-data'),
]
