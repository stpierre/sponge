import logging
from sponge.utils import messages, user as user_utils
from sponge.utils.decorators import template, superuser_required
from sponge.forms import DeleteOkayForm
from sponge.forms.user import UserForm
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from pulp.client.api.user import UserAPI
from pulp.client.api.role import RoleAPI
from pulp.client.api.server import ServerRequestError

logger = logging.getLogger(__name__)

@superuser_required()
@template("users.html")
def list(request):
    """ list users """
    return dict(users=user_utils.list_users().values())

@superuser_required()
@template("adduser.html")
def add(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            userapi = UserAPI()
            roleapi = RoleAPI()
            try:
                userapi.create(data['login'],
                               password=data['password'],
                               name=data['name'])
                messages.success(request,
                                 "Created user %s (%s)" %
                                 (data['name'], data['login']))
            except ServerRequestError, err:
                messages.error(request,
                               "Failed to create user %s (%s): %s" %
                               (data['name'], data['login'], err[1]))
                return dict(form=form)

            for role in data['roles']:
                try:
                    roleapi.add_user(role, data['login'])
                    messages.success(request,
                                     "Added role %s to user %s" %
                                     (role, data['name']))
                except ServerRequestError, err:
                    messages.error(request,
                                   "Failed to add role %s to user %s: %s" %
                                   (role, data['name'], err[1]))
            
            return HttpResponseRedirect(reverse('sponge.views.users.list'))
    return dict(form=UserForm())

@superuser_required()
@template("viewuser.html")
def view(request, login=None):
    userapi = UserAPI()
    user = user_utils.get_user(login)
    if request.method == 'POST':
        form = UserForm(request.POST, user=user)
        if form.is_valid():
            success = True
            delta = dict(name=form.cleaned_data['name'])
            if form.cleaned_data['password']:
                delta['password'] = form.cleaned_data['password']
            try:
                userapi.update(login, delta)
                messages.success(request,
                                 "Updated user information for %s" %
                                  user['name'])
            except ServerRequestError, err:
                success = False
                messages.error(request,
                               "Failed to update user information for %s: %s" %
                               (user['name'], err[1]))
            
            roleapi = RoleAPI()
            orig = [r
                    for r in form.cleaned_data['orig_roles'].splitlines()
                    if r]
            new = [r for r in form.cleaned_data['roles'] if r]
            to_remove = [r for r in orig if r not in new]
            for role in to_remove:
                try:
                    roleapi.remove_user(role, login)
                    messages.success(request,
                                     "Removed role %s from user %s" %
                                     (role, user['name']))
                except ServerRequestError, err:
                    success = False
                    messages.error(request,
                                   "Failed to remove role %s from user %s: %s"
                                   % (role, user['name'], err[1]))
            to_add = [r for r in new if r not in orig]
            for role in to_add:
                try:
                    roleapi.add_user(role, login)
                    messages.success(request,
                                     "Added role %s to user %s" %
                                     (role, user['name']))
                except ServerRequestError, err:
                    success = False
                    messages.error(request,
                                   "Failed to add role %s to user %s: %s" %
                                   (role, user['name'], err[1]))

            if success:
                return \
                    HttpResponseRedirect(reverse('sponge.views.users.list'))

    return dict(user=user,
                form=UserForm(user=user))


@superuser_required()
@template("deleteuser.html")
def delete(request, login=None):
    userapi = UserAPI()
    user = userapi.user(login)
    if request.method == 'POST':
        form = DeleteOkayForm(request.POST)
        if form.is_valid():
            try:
                userapi.delete(login=login)
                messages.success(request,
                                 "Deleted user %s (%s)" %
                                 (user['name'], user['login']))
                return \
                    HttpResponseRedirect(reverse('sponge.views.users.list'))
            except ServerRequestError, err:
                messages.error(request,
                               "Failed to delete user %s (%s): %s"
                               (user['name'], user['login'], err[1]))
    return dict(user=user,
                form=DeleteOkayForm(dict(id=login)))
