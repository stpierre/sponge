from django import forms
from django.forms import widgets
from sponge.utils import repo as repo_utils
from sponge.models import PackageSetPackage
from sponge.forms import LabelWidget
from pulp.client.api.repository import RepositoryAPI
import logging

logger = logging.getLogger(__name__)


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
