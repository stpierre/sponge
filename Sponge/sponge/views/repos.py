import re
import logging
from sponge.utils import messages, get_config, repo as repo_utils
from sponge.utils.decorators import template
from sponge.forms import DeleteOkayForm
from sponge.forms.package import PromotePackageSelectionForm, PromoteOkayForm, \
     DemotePackageSelectionForm, DemoteOkayForm
from sponge.forms.repo import RepoCloneForm, RepoEditForm, DiffSelectForm, \
     RepoAddForm
from sponge.tasks import CreateRepo, CloneRepo, SyncRepo, RebuildMetadata
from sponge.models import PackageSet, PackageSetRepo, PackageSetPackage
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from pulp.client.api.repository import RepositoryAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.api.server import ServerRequestError

logger = logging.getLogger(__name__)

@template("repos.html")
def list(request):
    """ list repos """
    repos = repo_utils.get_repos().values()
    return dict(repositories=repo_utils.sort_repos_by_ancestry(repos))

@template("viewrepo.html")
def view(request, repo_id=None):
    repoapi = RepositoryAPI()
    repo = repo_utils.get_repo(repo_id)
    packages = repoapi.packages(repo_id)
    for pkg in packages:
        pkg['nevra'] = repo_utils.get_nevra(pkg, repo['arch'])
    editform = RepoEditForm(repo=repo)
    diffform = DiffSelectForm()
    if request.method == 'POST' and "repoedit" in request.POST:
        editform = RepoEditForm(request.POST, repo=repo)
        if editform.is_valid():
            success = True
            if editform.cleaned_data['name'] != repo['name']:
                try:
                    repoapi.update(repo['id'],
                                   dict(name=editform.cleaned_data['name'],
                                        checksum_type=editform.cleaned_data['cksum']))
                    messages.debug(request,
                                   "Updated repository name for %s" %
                                   repo['id'])
                except ServerRequestError, err:
                    success = False
                    messages.error(request,
                                   "Could not update repository info for %s: "
                                   "%s" % (repo['id'], err[1]))

            groups = filter(lambda s: s != '',
                            editform.cleaned_data['groups'] + \
                            re.split(r'\s*,\s*',
                                     editform.cleaned_data['newgroups']))
            success &= repo_utils.set_groups(repo, groups, request=request)

            success &= repo_utils.set_gpgkeys(repo,
                                              editform.cleaned_data['gpgkeys'].splitlines(),
                                              request=request)
            success &= repo_utils.set_filters(repo,
                                              editform.cleaned_data['filters'],
                                              request=request)

            if success:
                messages.success(request, "Updated repository %s" % repo['id'])
            else:
                messages.warn(request,
                              "Errors encountered while updating repository %s"
                              % repo['id'])
            repo = repo_utils.reload_repo(repo['id'])
    elif request.method == 'POST' and "diffselect" in request.POST:
        diffform = DiffSelectForm(request.POST)
        if diffform.is_valid():
            return HttpResponseRedirect(reverse('sponge.views.repos.diff',
                                                kwargs=dict(repo_id=repo_id,
                                                            repo_id2=diffform.cleaned_data['repo2'])))

    return dict(repo=repo, editform=editform, diffform=diffform,
                packages=packages)

@template("addrepo.html")
def add(request):
    form = RepoAddForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            repo_id = "%s-%s-%s-%s" % (form.cleaned_data['os'],
                                       form.cleaned_data['version'],
                                       form.cleaned_data['arch'],
                                       form.cleaned_data['repo'])

            if form.cleaned_data['name']:
                name = form.cleaned_data['name']
            else:
                name = "%s %s %s - %s" % (form.cleaned_data['os'].title(),
                                          form.cleaned_data['version'],
                                          form.cleaned_data['arch'],
                                          form.cleaned_data['repo'])
            
            groups = filter(lambda s: s != '',
                            form.cleaned_data['groups'] + \
                            re.split(r'\s*,\s*',
                                     form.cleaned_data['newgroups']))
            CreateRepo.delay(repo_id,
                             groups=groups,
                             name=name,
                             arch=form.cleaned_data['arch'],
                             url=form.cleaned_data['url'],
                             gpgkeys=form.cleaned_data['gpgkeys'].splitlines(),
                             cksum=form.cleaned_data['cksum'],
                             filters=form.cleaned_data['filters'],
                             user=request.user.username)
            messages.success(request,
                             "Creation of repository %s enqueued" % repo_id)
            return HttpResponseRedirect(reverse('sponge.views.repos.list'))
    return dict(form=form)

@template("clone.html")
def clone(request, repo_id=None):
    repo = repo_utils.get_repo(repo_id)
    form = RepoCloneForm(request.POST or None, repo=repo)
    if request.method == 'POST':
        if form.is_valid():
            groups = filter(lambda s: s != '',
                            form.cleaned_data['groups'] + \
                            re.split(r'\s*,\s*',
                                     form.cleaned_data['newgroups']))

            clone_id = "%s-%s" % (form.cleaned_data["clone_id"], repo['id'])
            CloneRepo.delay(clone_id,
                            parent=repo,
                            name=form.cleaned_data["clone_name"],
                            groups=groups,
                            filters=form.cleaned_data['filters'],
                            user=request.user.username)
            return HttpResponseRedirect(reverse('sponge.views.repos.list'))
    return dict(repo=repo, form=form)

@template("deleterepo.html")
def delete(request, repo_id=None):
    repo = repo_utils.get_repo(repo_id)
    form = DeleteOkayForm(request.POST or None, dict(id=repo_id))
    if request.method == 'POST':
        if form.is_valid():
            repoapi = RepositoryAPI()
            try:
                repoapi.delete(repo_id)
                messages.success(request,
                                 "Deleted repository %s (%s)" %
                                 (repo['name'], repo['id']))
                return \
                    HttpResponseRedirect(reverse('sponge.views.repos.list'))
            except ServerRequestError, err:
                messages.error(request,
                               "Failed to delete repository %s (%s): %s"
                               (repo['name'], repo['id'], err[1]))
    return dict(repo=repo, form=form)


@template("promote_select.html")
def promote_select(request, repo_id=None):
    repo = repo_utils.get_repo(repo_id)
    form = PromotePackageSelectionForm(request.POST or None, repo=repo)
    if request.method == 'POST':
        repoapi = RepositoryAPI()
        pset = repo_utils.package_select(request, repo=repo,
                                         stype="promote",
                                         formcls=PromotePackageSelectionForm)
        packages = PackageSetPackage.objects.filter(packageset=pset.pk)
        deps = repo_utils.resolve_deps(packages,
                                       [repo['parent']['id']],
                                       pkgfilter=repoapi.packages(repo['id']))
        for pkg in deps:
            pkg = PackageSetPackage.objects.create(packageset=pset,
                                                   packageid=pkg['id'],
                                                   nevra=repo_utils.get_nevra(pkg))
            pkg.save()
        return HttpResponseRedirect(reverse('sponge.views.repos.promote_ok',
                                            kwargs=dict(pid=pset.pk)))
    packages = repo_utils.get_updates(repo)
    if packages:
        return dict(repo=repo, form=form)
    else:
        messages.info(request,
                      "No packages available to be promoted from %s to %s" %
                      (repo['parent']['name'], repo['name']))
        return HttpResponseRedirect(reverse('sponge.views.repos.list'))

@template("promote_ok.html")
def promote_ok(request, pid=None):
    pset = PackageSet.objects.get(pk=pid)
    repos = PackageSetRepo.objects.filter(packageset=pset.pk)
    form = PromoteOkayForm(request.POST or None, pset=pset)
    if request.POST:
        repoapi = RepositoryAPI()
        packages = PackageSetPackage.objects.filter(packageset=pset.pk)
        success = True
        logger.info("Promoting %s to repo(s) %s" %
                    ([p.packageid for p in packages],
                     [r.repoid for r in repos]))
        for repo in repos:
            try:
                errors = repoapi.add_package(repo.repoid,
                                             [p.packageid for p in packages])
                for error in errors:
                    if error[4]:
                        success = False
                        messages.warning(request,
                                         "Failed to add package %s to %s: %s" %
                                         (error[2], repo.repoid, error[4]))
            except ServerRequestError, err:
                success = False
                messages.error(request,
                               "Failed to add packages to %s (%s): %s" %
                               (repo.repoid,
                                ", ".join([p.nevra for p in packages]),
                                err[1]))

        if success:
            messages.success(request,
                             "Successfully added packages to repo(s) %s: %s" %
                             (",".join([r.name for r in repos]),
                              ", ".join([p.nevra for p in packages])))
        pset.delete()
        if len(repos) == 1:
            nexturl = reverse("sponge.views.repos.view",
                              kwargs=dict(repo_id=repos[0].repoid))
        else:
            nexturl = reverse("sponge.views.repos.list")
        return HttpResponseRedirect(nexturl)

    return dict(form=form,
                repos=[repo_utils.get_repo(r.repoid) for r in repos])

@template("promote_select_repos.html")
def promote_package(request, repo_id=None, package=None):
    repo = repo_utils.get_repo(repo_id)
    pkgid = package
    package = repo_utils.get_package(repo, id=pkgid)
    if len(repo['children']) > 1:
        children = [(r['id'], r['name']) for r in repo.children]
        form = PromoteRepoSelectionForm(request.POST or None, repos=children)
        if request.method == 'POST':
            pset = PackageSet.objects.create(stype="promote")
            pset.save()
            for prid in form.cleaned_data['repos']:
                prepo = repo_utils.get_repo(prid)
                psrepo = PackageSetRepo.objects.create(packageset=pset,
                                                       repoid=prepo['id'],
                                                       name=prepo['name'])
                psrepo.save()
            pkg = PackageSetPackage.objects.create(packageset=pset,
                                                   packageid=pkgid,
                                                   nevra=repo_utils.get_nevra(package))
        pkg.save()
        return dict(repo=repo, package=package, form=form)
    else:
        pset = PackageSet.objects.create(stype="promote")
        pset.save()
        prepo = PackageSetRepo.objects.create(packageset=pset,
                                              repoid=repo['children'][0]['id'],
                                              name=repo['name'])
        prepo.save()
        pkg = PackageSetPackage.objects.create(packageset=pset,
                                               packageid=pkgid,
                                               nevra=repo_utils.get_nevra(package))
        pkg.save()
        return HttpResponseRedirect(reverse("sponge.views.repos.promote_ok",
                                            kwargs=dict(pid=pset.pk)))

@template("demote_select.html")
def demote_select(request, repo_id=None):
    repo = repo_utils.get_repo(repo_id)
    form = DemotePackageSelectionForm(request.POST or None, repo=repo)
    if request.method == 'POST':
        pset = repo_utils.package_select(request, repo=repo,
                                         stype="demote",
                                         formcls=DemotePackageSelectionForm)
        return HttpResponseRedirect(reverse('sponge.views.repos.demote_ok',
                                            kwargs=dict(pid=pset.pk)))
    else:
        packages = repo_utils.get_updates(repo)
        return dict(repo=repo, form=form)

@template("demote_ok.html")
def demote_ok(request, pid=None):
    pset = PackageSet.objects.get(pk=pid)
    form = DemoteOkayForm(request.POST or None, pset=pset)
    repos = PackageSetRepo.objects.filter(packageset=pset.pk)
    
    if request.method == 'POST':
        repoapi = RepositoryAPI()
        packages = PackageSetPackage.objects.filter(packageset=pset.pk)        
        success = True
        
        for repo in repos:
            logger.info("Deleting %s from repo %s" %
                        ([p.nevra for p in packages], repo.repoid))
            for pkgobj in packages:
                package = repo_utils.get_package(repo.repoid,
                                                 id=pkgobj.packageid)

                if package is None:
                    success = False
                    messages.warning(request,
                                     "Failed to load package object for %s" %
                                     pkg.nevra)
                    continue
            
                try:
                    if not repoapi.remove_package(repo.repoid,
                                                  pkgobj=[package]):
                        success = False
                        messages.warning(request,
                                         "Failed to remove package %s from %s"
                                         % (repo_utils.get_nevra(package),
                                            repo.name))
                except ServerRequestError, err:
                    success = False
                    messages.error(request,
                                   "Failed to remove package %s from %s: %s" %
                                   (repo_utils.get_nevra(package),
                                    repo.name,
                                    err[1]))

        if success:
            messages.success(request,
                             "Successfully removed %s from %s" %
                             (", ".join([p.nevra for p in packages]),
                              ", ".join([r.name for r in repos])))
        pset.delete()
        if len(repos) == 1:
            nexturl = reverse("sponge.views.repos.view",
                           kwargs=dict(repo_id=repos[0].repoid))
        else:
            nexturl = reverse("sponge.views.repos.list")
        return HttpResponseRedirect(nexturl)

    return dict(form=form,
                repos=[repo_utils.get_repo(r.repoid) for r in repos])

def demote_package(request, repo_id=None, package=None):
    repo = repo_utils.get_repo(repo_id)
    pkgid = package
    package = repo_utils.get_package(repo, id=pkgid)
    pset = PackageSet.objects.create(stype="demote")
    pset.save()
    prepo = PackageSetRepo.objects.create(packageset=pset,
                                          repoid=repo['id'],
                                          name=repo['name'])
    prepo.save()
    pkg = PackageSetPackage.objects.create(packageset=pset,
                                           packageid=pkgid,
                                           nevra=repo_utils.get_nevra(package))
    pkg.save()
    return HttpResponseRedirect(reverse("sponge.views.repos.demote_ok",
                                        kwargs=dict(pid=pset.pk)))

@template("diff.html")
def diff(request, repo_id=None, repo_id2=None):
    repoapi = RepositoryAPI()
    if request.GET:
        mode = request.GET.get("mode", "all")
    else:
        mode = "all"
    
    repo1 = repo_utils.get_repo(repo_id)
    repo2 = repo_utils.get_repo(repo_id2)
    packages1 = dict([(p['name'], p) for p in repoapi.packages(repo_id)])
    packages2 = dict([(p['name'], p) for p in repoapi.packages(repo_id2)])
    pkg_names = set(packages1.keys() + packages2.keys())
    allpackages = dict()
    for pkg in pkg_names:
        if pkg in packages1:
            nevra1 = repo_utils.get_nevra(packages1[pkg])
        else:
            nevra1 = None
        if pkg in packages2:
            nevra2 = repo_utils.get_nevra(packages2[pkg])
        else:
            nevra2 = None
        if nevra1 == nevra2 and mode == "diff":
            continue
        
        allpackages[pkg] = dict()
        allpackages[pkg]["repo1"] = nevra1
        allpackages[pkg]["repo2"] = nevra2

    return dict(repo1=repo1, repo2=repo2, mode=mode,
                packages1=packages1, packages2=packages2,
                allpackages=allpackages)

def sync(request, repo_id=None):
    SyncRepo.delay(repo_id, user=request.user.username)
    messages.success(request, "Sync of %s started" % repo_id)
    if request.GET and request.GET['next']:
        return HttpResponseRedirect(request.GET['next'])
    else:
        return HttpResponseRedirect(reverse('sponge.views.repos.list'))

def rebuild_metadata(request, repo_id=None):
    RebuildMetadata.delay(repo_id, user=request.user.username)
    messages.success(request, "Rebuild of metadata for %s started" % repo_id)
    if request.GET and request.GET['next']:
        return HttpResponseRedirect(request.GET['next'])
    else:
        return HttpResponseRedirect(reverse('sponge.views.repos.list'))
