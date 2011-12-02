from django import forms
from django.forms import widgets
from django.forms.forms import pretty_name
from sponge.utils import config as config_utils

class ConfigItem(object):
    def __init__(self, name, label=None, default=None, description=None,
                 field=None, widget=None):
        self.name = name
        if label is None:
            self.label = pretty_name(name)
        else:
            self.label = label
        self.default = default
        self.description = description
        if field is None:
            self.field = forms.CharField
        else:
            self.field = field
        self.widget = widget


class ConfigForm(forms.Form):
    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        for item in _config_items:
            self.fields[item.name] = \
                item.field(label=item.label,
                           initial=config_utils.get(item.name,
                                                    item.default),
                           help_text=item.description,
                           widget=item.widget)


_config_items = \
    [ConfigItem("sync_frequency",
                default=24,
                description="The frequency, in hours, with which to sync all repositories",
                field=forms.IntegerField),
     ConfigItem("scheduler_username",
                description="The username of a Pulp user who can modify all sync schedules. Granting 'read' and 'update' on '/repositories/' should be sufficient."),
     ConfigItem("scheduler_password",
                description="The password for the sync schedule user",
                widget=widgets.PasswordInput())]
