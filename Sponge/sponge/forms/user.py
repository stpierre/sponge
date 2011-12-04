from django import forms
from django.forms import widgets
from sponge.utils import role as role_utils, user as user_utils
from sponge.forms import DisplayWidget
import logging

logger = logging.getLogger(__name__)


class UserForm(forms.Form):
    login = forms.CharField()
    name = forms.CharField()
    password = forms.CharField(widget=widgets.PasswordInput(),
                               required=False)
    roles = \
        forms.MultipleChoiceField(choices=[(rid, r['name'])
                                           for rid, r in \
                                               role_utils.list_roles().items()])
    def __init__(self, *args, **kwargs):
        user = None
        if "user" in kwargs:
            user = kwargs.pop("user")
        kwargs['initial'] = user
        forms.Form.__init__(self, *args, **kwargs)
        if user is not None:
            self.fields['login'].widget = DisplayWidget()
            self.fields['login'].required = False
            self.fields["orig_roles"] = \
                forms.CharField(initial="\n".join(user['roles']),
                                widget=widgets.HiddenInput())
