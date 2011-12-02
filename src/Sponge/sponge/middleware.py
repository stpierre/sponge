import os
import logging
import tempfile
from M2Crypto.BIO import BIOError
from pulp.client.api import server
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.views import login, redirect_to_login
from sponge.utils import get_pulp_server, messages
from sponge.models import CeleryTaskTracker
from sponge import tasks

logger = logging.getLogger(__name__)

class PulpServerMiddleware(object):
    """ Loads a pulp server before every request; requires
    authentication on all pages """
    def __init__(self):
        self.require_login_path = getattr(settings,
                                          'REQUIRE_LOGIN_PATH',
                                          '/login/')

    def process_request(self, request):
        if (request.path != self.require_login_path and
            request.user.is_anonymous()):
            if request.POST:
                return login(request)
            else:
                return redirect_to_login(request.path, self.require_login_path)
        elif not request.user.is_anonymous():
            try:
                pulpserver = get_pulp_server(user=request.user.username)
            except (BIOError, server.ServerRequestError), err:
                logger.warning("Session for %s expired" %
                               request.user.username)
                logout(request)
                messages.warning(request, "Your session has expired")
                return redirect_to_login(request.path, self.require_login_path)
            except IOError, err:
                logger.info(err)
                logout(request)
                return redirect_to_login(request.path, self.require_login_path)
        return None


class CeleryTaskTrackerMiddleware(object):
    def process_request(self, request):
        tasklist = CeleryTaskTracker.objects.filter(owner=request.user.username)
        for task in tasklist:
            tclass = getattr(tasks, task.taskclass)
            status = tclass.AsyncResult(task.taskid)
            if status.info:
                if status.failed() or status.state == "ERROR":
                    messages.error(request, str(status.info))
                    task.delete()
                elif status.state == "PROGRESS":
                    messages.info(request, status.info)
                elif status.state == "SUCCESS":
                    messages.success(request, status.info)
                    task.delete()
            status.forget()

        return None
