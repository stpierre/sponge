from django import forms
from django.forms import widgets
from sponge.utils import config as config_utils
from sponge.utils import group as group_utils

class ConfigForm(forms.Form):
    scheduler_username = forms.CharField(help_text="The username of a Pulp user who can modify all sync schedules. Granting 'read' and 'update' on '/repositories/' should be sufficient.")
    scheduler_password = forms.CharField(help_text="The password for the sync schedule user",
                                         widget=widgets.PasswordInput(),
                                         required=False)

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)

        self.fields['scheduler_username'].initial = \
            config_utils.get('scheduler_username', None)

        # i wish django supported fieldsets
        for group in group_utils.get_groups():
            cname = "sync_frequency_%s" % group
            self.fields[cname] = \
                forms.IntegerField(label="Sync frequency for %s" % group,
                                   help_text="The frequency, in hours, with which to sync all repositories in group %s" % group,
                                   initial=config_utils.get(cname, 24))

        if "default" not in group_utils.get_groups():
            self.fields['default'] = \
                forms.IntegerField(label="Default sync frequency",
                                   help_text="If a machine is in no groups, the frequency, in hours, with which to sync it",
                                   initial=config_utils.get("sync_frequency_default", 24))
