from django.conf import settings
from django.conf.urls.defaults import *

urlpatterns = patterns('sponge.views.repos',
    (r'^$', 'list'),
    (r'^repo/$', 'list'),
    (r'^repo/add/$', 'add'),
    (r'^repo/(?P<repo_id>[^/]+)/$', 'view'),
    (r'^repo/(?P<repo_id>[^/]+)/delete/$', 'delete'),
    (r'^repo/(?P<repo_id>[^/]+)/promote/$', 'promote_select'),
    (r'^repo/promote/(?P<pid>\d+)$', 'promote_ok'),
    (r'^repo/(?P<repo_id>[^/]+)/demote/$', 'demote_select'),
    (r'^repo/demote/(?P<pid>\d+)$', 'demote_ok'),
    (r'^repo/(?P<repo_id>[^/]+)/promote/package/(?P<package>[a-z0-9\-]+)$',
     'promote_package'),
    (r'^repo/(?P<repo_id>[^/]+)/demote/package/(?P<package>[a-z0-9\-]+)$',
     'demote_package'),
    (r'^repo/(?P<repo_id>[^/]+)/diff/(?P<repo_id2>[^/]+)/$', 'diff'),
    (r'^repo/(?P<repo_id>[^/]+)/sync/$', 'sync'),
    (r'^repo/(?P<repo_id>[^/]+)/rebuild/$', 'rebuild_metadata'),
    (r'^repo/(?P<repo_id>[^/]+)/clone/$', 'clone'))

urlpatterns += patterns('sponge.views.filters',
    (r'^filter/$', 'list'),
    (r'^filter/add/$', 'add'),
    (r'^filter/(?P<filter_id>[^/]+)/$', 'view'),
    (r'^filter/(?P<filter_id>[^/]+)/delete/$', 'delete'))

urlpatterns += patterns('sponge.views.users',
    (r'^users/$', 'list'),
    (r'^users/add/$', 'add'),
    (r'^users/(?P<login>[^/]+)/$', 'view'),
    (r'^users/(?P<login>[^/]+)/delete/$', 'delete'))

urlpatterns += patterns('sponge.views.tasks',
    (r'^tasks/$', 'list'),
    (r'^tasks/(?P<task_id>[^/]+)/delete/$', 'delete'))

urlpatterns += patterns('',
    (r'^login/$', 'django.contrib.auth.views.login',
     {'template_name': 'login.html'}),
    (r'^logout/$', 'sponge.views.logout'),
    (r'^config/$', 'sponge.views.configure'),
    )

if settings.DEBUG:
    from django.views.static import serve
    _media_url = settings.MEDIA_URL
    if _media_url.startswith('/'):
        _media_url = _media_url[1:]
        urlpatterns += patterns('',
                                (r'^%s(?P<path>.*)$' % _media_url,
                                 serve,
                                 {'document_root': settings.MEDIA_ROOT}))
    del(_media_url, serve)
