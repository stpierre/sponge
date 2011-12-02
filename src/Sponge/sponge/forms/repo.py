from django import forms
from django.forms import widgets
from sponge.utils import repo as repo_utils
from sponge.utils import filter as filter_utils
from sponge.utils import group as group_utils
from sponge.forms import DisplayWidget, CloneIdWidget
import logging

logger = logging.getLogger(__name__)


class PromoteRepoSelectionForm(forms.Form):
    repos = forms.MultipleChoiceField(label="Repositories",
                                      widget=widgets.CheckboxSelectMultiple())


class RepoAddForm(forms.Form):
    os = forms.CharField(label="OS",
                         help_text="All lower-case.  E.g., 'sles', 'centos', 'generic', etc.")
    version = \
        forms.CharField(label="Version",
                        help_text="For RHEL-like OSes, include just the major version.")
    arch = forms.ChoiceField(label="Architecture",
                             initial="x86_64",
                             choices=[("x86_64", "x86_64"),
                                      ("i386", "i386"),
                                      ("noarch", "noarch"),
                                      ("ppc", "ppc"),
                                      ("ppc64", "ppc64")])
    repo = forms.CharField(label="Repository",
                           help_text="All lower-case, no spaces.  E.g., 'ius', 'updates', 'vmware-tools', etc.")
    name = forms.CharField(label="Repository Name",
                           required=False,
                           help_text="The name must contain the OS, version, arch, and repository name.  If you do not enter a name, one will be automatically generated; this is usually the right choice.")
    cksum = forms.ChoiceField(label="Checksum Type",
                              initial="sha1",
                              choices=[("sha1", "sha1"),
                                       ("sha256", "sha256")],
                              help_text="Select 'sha1' for the checksum type for all SLES distros, RHEL/CentOS 5 or earlier, and Fedora 12 and earlier. For RHEL/CentOS 6 and Fedora >= 13, pick 'sha256.' If in doubt, use 'sha1.'")
    gpgkeys = \
        forms.CharField(label="GPG Keys",
                        required=False,
                        help_text="Enter URLs to GPG keys, one per line",
                        widget=widgets.Textarea(attrs=dict(rows=5, cols=80)))
    url = forms.CharField("Feed URL")
    groups = forms.MultipleChoiceField(label="Groups",
                                       required=False,
                                       choices=[(g, g)
                                                for g in group_utils.get_groups()],
                                       widget=widgets.CheckboxSelectMultiple())
    newgroups = \
        forms.CharField(label="New Groups",
                        required=False,
                        help_text="Add new repository groups, separated by commas")
    filters = forms.MultipleChoiceField(label="Filters",
                                        required=False,
                                        choices=[(fid, f['description'])
                                                 for fid, f in filter_utils.list_filters().items()],
                                        widget=widgets.CheckboxSelectMultiple())


class RepoEditBase(forms.Form):
    def __init__(self, *args, **kwargs):
        self.repo = kwargs.pop("repo")
        forms.Form.__init__(self, *args, **kwargs)

        self.extra_fields()

        self.fields['groups'] = \
            forms.MultipleChoiceField(label="Groups",
                                      initial=self.repo['groupid'],
                                      required=False,
                                      choices=[(g, g)
                                               for g in group_utils.get_groups()],
                                      widget=widgets.CheckboxSelectMultiple())
        self.fields['newgroups'] = \
            forms.CharField(label="New Groups",
                            required=False,
                            help_text="Add new repository groups, separated by commas")
        self.fields['filters'] = \
            forms.MultipleChoiceField(label="Filters",
                                      initial=self.repo['filters'],
                                      required=False,
                                      choices=[(fid, f['description'])
                                               for fid, f in filter_utils.list_filters().items()],
                                      widget=widgets.CheckboxSelectMultiple())


class RepoCloneForm(RepoEditBase):
    def extra_fields(self):
        self.fields['parent_id'] = forms.CharField(widget=widgets.HiddenInput(),
                                                   initial=self.repo['id'],
                                                   required=False)
        self.fields['clone_id'] = \
            forms.CharField(label="Clone ID",
                            widget=CloneIdWidget(repo_utils.get_branch_id(self.repo)),
                            help_text="The repository ID of the ultimate ancestor of this repository will be automatically appended")
        self.fields['clone_name'] = forms.CharField(label="Clone Name")


class RepoEditForm(RepoEditBase):
    def extra_fields(self):
        self.fields['name'] = forms.CharField(label="Name",
                                              initial=self.repo['name'])
        self.fields['id'] = forms.CharField(label="ID",
                                            required=False,
                                            initial=self.repo['id'],
                                            widget=DisplayWidget())

        self.fields['cksum'] = forms.ChoiceField(label="Checksum Type",
                                                 initial="sha1",
                                                 choices=[("sha1", "sha1"),
                                                          ("sha256", "sha256")])

        self.fields['gpgkeys'] = \
            forms.CharField(initial="\n".join(self.repo['keys'].values()),
                            required=False,
                            label="GPG Keys",
                            help_text="Enter URLs to GPG keys, one per line",
                            widget=widgets.Textarea(attrs=dict(rows=5,
                                                               cols=80)))


class DiffSelectForm(forms.Form):
    repo2 = \
        forms.ChoiceField(label="Diff this repository with",
                          required=True,
                          choices=[(r['id'], r['name'])
                                   for r in repo_utils.sort_repos_by_ancestry(repo_utils.get_repos().values())])
