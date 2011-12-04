from django import forms
from django.forms import widgets
from django.utils.safestring import mark_safe
from sponge.utils import repo as repo_utils
from sponge.utils import filter as filter_utils
from sponge.utils import group as group_utils
from sponge.models import PackageSetPackage
from pulp.client.api.repository import RepositoryAPI
import logging

logger = logging.getLogger(__name__)


class LabelWidget(widgets.HiddenInput):
    """ hidden form input that does not hide the label """
    is_hidden = False


class DisplayWidget(widgets.Input):
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        return value


class CloneIdWidget(widgets.TextInput):
    def __init__(self, parent_id, attrs=None):
        widgets.TextInput.__init__(self, attrs=attrs)
        self.parent_id = parent_id
    
    def render(self, name, value, attrs=None):
        widget = widgets.TextInput.render(self, name, value, attrs=attrs)
        if self.parent_id:
            return mark_safe("%s-%s" % (widget, self.parent_id))
        else:
            return widget


class DeleteOkayForm(forms.Form):
    id = forms.CharField(widget=widgets.HiddenInput(),
                         required=False)
