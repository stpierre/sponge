from django import forms
from django.forms import widgets
from sponge.forms import DisplayWidget
import logging

logger = logging.getLogger(__name__)


class FilterForm(forms.Form):
    f_id = forms.CharField(label="ID")
    f_type = forms.ChoiceField(label="Type",
                               choices=[("blacklist", "Blacklist"),
                                        ("whitelist", "Whitelist")])
    desc = forms.CharField(label="Description")
    patterns = \
        forms.CharField(help_text="Enter regular expressions, one per line",
                        widget=widgets.Textarea(attrs=dict(rows=40)))

    def __init__(self, *args, **kwargs):
        fltr = None
        if "filter" in kwargs:
            fltr = kwargs.pop("filter")
            kwargs['initial'] = dict(f_id=fltr['id'],
                                     f_type=fltr['type'],
                                     desc=fltr['description'],
                                     patterns="\n".join(fltr['package_list']))
        forms.Form.__init__(self, *args, **kwargs)
        if fltr is not None:
            self.fields["f_id"].widget = DisplayWidget()
            self.fields["f_id"].required = False
            self.fields["f_type"].widget = DisplayWidget()
            self.fields["f_type"].required = False
            # description is currently read-only, so we use
            # DisplayWidget().  If that gets fixed in the Pulp API, we
            # can remove these lines
            self.fields["desc"].widget = DisplayWidget()
            self.fields["desc"].required = False
            self.fields["orig_patterns"] = \
                forms.CharField(initial="\n".join(fltr['package_list']),
                                widget=widgets.HiddenInput())
