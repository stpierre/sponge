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


class PackageSelectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        repo = kwargs.pop("repo")
        forms.Form.__init__(self, *args, **kwargs)
        self.repoapi = RepositoryAPI()

        for pkg in self.get_packages(repo):
            nevra = repo_utils.get_nevra(pkg, arch=repo['arch'])
            self.fields[pkg['id']] = forms.BooleanField(label=nevra,
                                                        required=False)

    def get_packages(self, repo):
        return []


class PromotePackageSelectionForm(PackageSelectionForm):
    def get_packages(self, repo):
        return repo_utils.get_updates(repo)


class DemotePackageSelectionForm(PackageSelectionForm):
    def get_packages(self, repo):
        return self.repoapi.packages(repo['id'])


class PackageOkayForm(forms.Form):
    def __init__(self, *args, **kwargs):
        if "pset" in kwargs:
            pset = kwargs.pop("pset")
            packages = dict([(p.packageid, p.nevra)
                             for p in PackageSetPackage.objects.filter(packageset=pset.pk)])
        elif "repo" in kwargs and "package" in kwargs:
            repo = repo_utils.get_repo(kwargs.pop("repo"))
            package = kwargs.pop("package")
            packages = {package['id']: repo_utils.get_nevra(package)}
                
        forms.Form.__init__(self, *args, **kwargs)
        self.label_suffix = ''

        for packageid, nevra in packages.items():
            self.fields[packageid] = forms.BooleanField(label=nevra,
                                                        initial=True,
                                                        widget=LabelWidget())


class PromoteOkayForm(PackageOkayForm):
    pass


class DemoteOkayForm(PackageOkayForm):
    pass


class PromoteRepoSelectionForm(forms.Form):
    repos = forms.MultipleChoiceField(label="Repositories",
                                      widget=widgets.CheckboxSelectMultiple())

class FilterEditForm(forms.Form):
    def __init__(self, *args, **kwargs):
        fltr = kwargs.pop("filter")
        forms.Form.__init__(self, *args, **kwargs)
        self.fields["f_id"] = forms.CharField(initial=fltr['id'],
                                              label="ID",
                                              widget=DisplayWidget(),
                                              required=False)
        self.fields["f_type"] = forms.CharField(initial=fltr['type'],
                                              label="Type",
                                              widget=DisplayWidget(),
                                              required=False)
        # description is currently read-only, so we use
        # DisplayWidget().  If that gets fixed in the Pulp API, we can
        # change remove that
        self.fields["desc"] = forms.CharField(initial=fltr['description'],
                                              label="Description",
                                              widget=DisplayWidget(),
                                              required=False)
        self.fields["orig_patterns"] = \
            forms.CharField(initial="\n".join(fltr['package_list']),
                            widget=widgets.HiddenInput())
        self.fields["patterns"] = \
            forms.CharField(initial="\n".join(fltr['package_list']),
                            label="Patterns",
                            help_text="Enter regular expressions, one per line",
                            widget=widgets.Textarea(attrs=dict(rows=40)))


class FilterAddForm(forms.Form):
    f_id = forms.CharField(label="ID")
    f_type = forms.ChoiceField(label="Type",
                               choices=[("blacklist", "Blacklist"),
                                        ("whitelist", "Whitelist")])
    desc = forms.CharField(label="Description")
    patterns = \
        forms.CharField(label="Patterns",
                        help_text="Enter regular expressions, one per line",
                        widget=widgets.Textarea(attrs=dict(rows=40)))


class DeleteOkayForm(forms.Form):
    id = forms.CharField(widget=widgets.HiddenInput(),
                         required=False)


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
                                       ("sha256", "sha256")])
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
        self.fields['id'] = \
            forms.CharField(label="ID",
                            required=False,
                            initial=self.repo['id'],
                            widget=DisplayWidget())

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
