from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^auth-redirect/$', views.trello_redirect, name='auth-redirect'),
    url(r'^api/v0/authenticate/$', views.authenticate_with_token, name='api-authenticate'),
]
