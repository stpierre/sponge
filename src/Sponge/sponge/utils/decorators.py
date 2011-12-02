import logging
from sponge.utils import messages, user as user_utils
from django.utils.functional import wraps
from django.http import HttpResponse, HttpResponseRedirect, \
     HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template import RequestContext
from pulp.client.api.server import ServerRequestError

logger = logging.getLogger(__name__)

class template(object):
    def __init__(self, template="default.html"):
        self.template = template

    def __call__(self, func):
        @wraps(func)
        def inner(request, *args, **kwargs):
            try:
                response = func(request, *args, **kwargs)
            except ServerRequestError, err:
                return HttpResponseForbidden(err[1])
            
            if (isinstance(response, HttpResponse) or
                isinstance(response, HttpResponseRedirect)):
                return response
            return render_to_response(self.template, response,
                                      context_instance=RequestContext(request))
        return inner


class superuser_required(object):
    def __init__(self, redirect="sponge.views.repos.list"):
        self.redirect = redirect

    def __call__(self, func):
        @wraps(func)
        def inner(request, *args, **kwargs):
            if user_utils.is_superuser(request.user.username):
                return func(request, *args, **kwargs)
            else:
                messages.error("Permission denied")
                return HttpResponseRedirect(self.redirect)

        return inner
