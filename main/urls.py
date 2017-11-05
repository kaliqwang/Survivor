from django.conf.urls import url

from .views import *

urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^login/$', user_login, name='login'),
    url(r'^logout/$', user_logout, name='logout'),
    url(r'^register/$', register, name='register'),
    url(r'^user-update/$', user_update, name='user-update'),
    url(r'^join-game/$', join_game, name='join-game'),
    url(r'^leave-game/$', leave_game, name='leave-game'),
    url(r'^create-game/$', create_game, name='create-game'),
    url(r'^close-game/$', close_game, name='close-game'),
    url(r'^update-game/$', update_game, name='update-game'),
    url(r'^start-game/$', start_game, name='start-game'),
    url(r'^killed-target/$', killed_target, name='killed-target'),
    url(r'^killed-attacker/$', killed_attacker, name='killed-attacker'),
    url(r'^eliminations/(?P<pk>\d+)/undo$', elimination_undo, name='elimination-undo'),
]
