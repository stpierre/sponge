import cPickle
import logging
from django import forms
from django.forms import widgets
from sponge.utils import repo as repo_utils
from sponge.models import PackageSetPackage
from sponge.forms import LabelWidget
from pulp.client.api.repository import RepositoryAPI

logger = logging.getLogger(__name__)


class PackageSelectionForm(forms.Form):
    packages = \
        forms.MultipleChoiceField(label="Packages",
                                  widget=widgets.CheckboxSelectMultiple())

    def __init__(self, *args, **kwargs):
        repo = kwargs.pop("repo")
        forms.Form.__init__(self, *args, **kwargs)

        self.fields['packages'].choices = []
        for pkg in self.get_packages(repo):
            nevra = repo_utils.get_nevra(pkg, arch=repo['arch'])
            self.fields['packages'].choices.append((pkg['id'], nevra))

    def get_packages(self, repo):
        return []


class PromotePackageSelectionForm(PackageSelectionForm):
    def get_packages(self, repo):
        return repo_utils.get_updates(repo)


class DemotePackageSelectionForm(PackageSelectionForm):
    def get_packages(self, repo):
        repoapi = RepositoryAPI()
        return repoapi.packages(repo['id'])


class PackageOkayForm(forms.Form):
    def __init__(self, *args, **kwargs):
        if "pset" in kwargs:
            pset = kwargs.pop("pset")
            packages = dict()
            for pspkg in PackageSetPackage.objects.filter(packageset=pset.pk):
                pkg = cPickle.loads(str(pspkg.pkgobj))
                packages[pkg['id']] = repo_utils.get_nevra(pkg)
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
