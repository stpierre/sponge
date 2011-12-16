""" repository functions """

import os
import time
import cPickle
import logging
import datetime
import threading
from urllib import urlopen
from sponge.models import PackageSet, PackageSetRepo, PackageSetPackage
from sponge.utils import get_pulp_server, get_config, messages, config
from pulp.client.api.repository import RepositoryAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.api.server import ServerRequestError
from pulp.client.api.task import TaskAPI, task_end, task_succeeded
from pulp.common.dateutils import format_iso8601_datetime, \
     format_iso8601_interval, parse_iso8601_datetime, parse_iso8601_interval
from pulp.client.lib.utils import parse_interval_schedule

logger = logging.getLogger(__name__)

def get_repos(reload=False):
    if reload:
        repos = None
    else:
        repos = getattr(threading.local(), "repos", None)
    if repos is None:
        # this looks inefficient, and it is, but repos has to be fully
        # loaded before we can call _load_repo_extras(), so we have to
        # do this in two separate loops
        repoapi = RepositoryAPI()
        repos = dict([(r['id'], r) for r in repoapi.repositories(dict())])
        for repo in repos.values():
            _load_repo_extras(repo, repos=repos)
        setattr(threading.local(), "repos", repos)
    return repos

def reload_repo(repo_id):
    repos = getattr(threading.local(), "repos", None)
    if repos is not None:
        repoapi = RepositoryAPI()
        repos[repo_id] = repoapi.repository(repo_id)
        _load_repo_extras(repos[repo_id])
    return get_repos()[repo_id]

def _load_repo_extras(repo, repos=None):
    config = get_config()
    repoapi = RepositoryAPI()
    repo['url'] = os.path.join(config.cds.baseurl,
                               repo['relative_path'])

    repo['parent'] = None
    repo['children'] = []
    if repos is None:
        repos = getattr(threading.local(), "repos", dict())
        
    for repo2 in repos.values():
        if repo2 == repo:
            continue
        elif repo['id'] in repo2['clone_ids']:
            # the clone_id attribute is broken, but we check it anyway
            # just in case it gets fixed some day
            repo['parent'] = repo2
        elif repo2['id'] in repo['clone_ids']:
            repo['children'].append(repo2)
        elif (repo['id'].endswith(repo2['id']) and
              repo['source']['url'].endswith("/%s" % repo2['id'])):
            # this check is wonky, but it works with our setup: the
            # child repo's id ends with the parent repo's id, and the
            # child syncs from a local repo that ends with /<parent
            # repo id>.  i'm sure there's a crazy edge case where this
            # is wrong, but it works well enough for now
            repo['parent'] = repo2
        elif (repo2['id'].endswith(repo['id']) and
              repo2['source']['url'].endswith("/%s" % repo['id'])):
            repo['children'].append(repo2)

    repo['keys'] = dict()
    for key in repoapi.listkeys(repo['id']):
        repo['keys'][os.path.basename(key)] = "%s/%s" % (config.cds.keyurl, key)

    if repo['parent']:
        repo['updates'] = has_updates(repo)

    if repo['last_sync'] and repo['sync_schedule']:
        repo['next_sync'] = \
            format_iso8601_datetime(parse_iso8601_datetime(repo['last_sync']) +
                                    parse_iso8601_interval(repo['sync_schedule'])[0])
    elif repo['sync_schedule']:
        repo['next_sync'] = \
            format_iso8601_datetime(parse_iso8601_interval(repo['sync_schedule'])[1])
    else:
        repo['next_sync'] = None

def is_child(repo, repositories=None):
    """ determine if a repository is a child of another repository """
    return getparent(repo, repositories=repositories) is not None

def get_repo(repo):
    """ load a repository and its parent """
    if isinstance(repo, dict):
        repo = repo['id']
    repos = get_repos()
    if repo in repos:
        return repos[repo]
    else:
        return get_repos(reload=True)[repo]

def get_package(repo, name=None, id=None):
    if not isinstance(repo, dict):
        repo = get_repo(repo)
    repoapi = RepositoryAPI()
    for pkg in repoapi.packages(repo['id']):
        if (pkg['id'] == id or
            pkg['name'] == name or
            get_nevra(pkg) == name or
            get_nevra(pkg, arch=repo['arch']) == name or
            "%s-%s" % (pkg['name'], pkg['version']) == name):
            return pkg
    return None

def has_updates(repo):
    """ determine if a child repository has updates available """
    if not repo['parent']:
        return False

    if repo['package_count'] < repo['parent']['package_count']:
        # attempt to short-circuit the very time-consuming count_updates()
        return True

    # count_updates() takes too long until we get some reasonable
    # caching in place.  for now just return True
    return True
    return bool(count_updates(repo))

def count_updates(repo):
    """ return the number of updated packages available to a repo """
    try:
        return len(get_updates(repo))
    except TypeError:
        return None

def get_updates(repo):
    """ return a list of updated packages available to a child repo """
    if not repo['parent']:
        return None

    repoapi = RepositoryAPI()
    child_nevras = [get_nevra(p) for p in repoapi.packages(repo['id'])]

    rv = []
    for pkg in repoapi.packages(repo['parent']['id']):
        if get_nevra(pkg) not in child_nevras:
            rv.append(pkg)

    return rv

def get_nevra(package, arch=None):
    if package['epoch'] != '0':
        epoch = "%s:" % package['epoch']
    else:
        epoch = ''
    
    if arch is None or package['arch'] != arch:
        arch = ".%s" % package['arch']
    else:
        arch = ''
    
    return "%s-%s%s-%s%s" % (package['name'], epoch, package['version'],
                             package['release'], arch)

def resolve_deps(packages, repos, pkgfilter=None):
    rv = []

    if pkgfilter is None:
        pkgfilter = []
    
    serviceapi = ServiceAPI()
    deps = serviceapi.dependencies([get_nevra(p) for p in packages],
                                   repos, recursive=True)
    child_nevras = [get_nevra(p) for p in pkgfilter]
    for dep in deps['resolved'].values():
        for pkg in dep:
            if get_nevra(pkg) not in child_nevras:
                rv.append(pkg)

    return rv

def sort_repos_by_ancestry(repos, parent=None):
    rv = []
    for repo in repos:
        if ((parent is None and repo['parent'] is None) or
            (parent is not None and repo['parent'] is not None and
             repo['parent']['id'] == parent['id'])):
            rv.append(repo)
            rv.extend(sort_repos_by_ancestry(repos, parent=repo))
    return rv

def remove_schedule(repo):
    repoapi = RepositoryAPI()
    rv = repo['sync_schedule']
    repoapi.delete_sync_schedule(repo['id'])
    reload_repo(repo['id'])
    return rv

def set_schedule(repo, schedule):
    repoapi = RepositoryAPI()
    repoapi.change_sync_schedule(repo['id'], dict(schedule=schedule,
                                                  options=dict()))
    reload_repo(repo['id'])
    return repo

restore_schedule = set_schedule

def get_branch_id(repo):
    """ get the repo id of a whole branch -- basically, of the
    ultimate ancestor.  for instance,
    get_branch_id('infra-stable-generic-6-x86_64-hp') should return
    'generic-6-x86_64-hp' """
    if repo['parent']:
        return get_branch_id(repo['parent'])
    else:
        return repo['id']

def set_groups(repo, groups, request=None, errors=None):
    repoapi = RepositoryAPI()
    if errors is None:
        errors = []
    for group in repo['groupid']:
        if group not in groups:
            try:
                repoapi.remove_group(repo['id'], group)
                if request:
                    messages.debug(request,
                                   "Removed group %s from %s" %
                                   (group, repo['id']))
            except ServerRequestError, err:
                errors.append("Could not remove group %s from %s: %s" %
                              (group, repo['id'], err[1]))

    for group in groups:
        if group not in repo['groupid']:
            try:
                repoapi.add_group(repo['id'], group)
                if request:
                    messages.debug("Added group %s to %s" %
                                   (group, repo['id']))
            except ServerRequestError, err:
                errors.append("Could not add group %s to %s: %s" %
                              (group, repo['id'], err[1]))

    reload_repo(repo['id'])
    if errors:
        if request:
            for err in errors:
                messages.error(request, err)
        return False
    else:
        return True

def set_filters(repo, filters, request=None, errors=None):
    repoapi = RepositoryAPI()
    if errors is None:
        errors = []
    to_remove = [f for f in repo['filters'] if f not in filters]
    if to_remove:
        try:
            repoapi.remove_filters(repo['id'], to_remove)
            if request:
                messages.debug(request,
                               "Removed filters %s from %s" %
                               (to_remove, repo['id']))
        except ServerRequestError, err:
            errors.append("Could not remove filters %s from %s: %s" %
                          (to_remove, repo['id'], err[1]))

    to_add = [f for f in filters if f not in repo['filters']]
    if to_add:
        try:
            repoapi.add_filters(repo['id'], to_add)
            if request:
                messages.debug("Added filters %s to %s" %
                               (to_add, repo['id']))
        except ServerRequestError, err:
            errors.append("Could not add filters %s to %s: %s" %
                          (to_add, repo['id'], err[1]))

    reload_repo(repo['id'])
    if errors:
        if request:
            for err in errors:
                messages.error(request, err)
        return False
    else:
        return True

def get_keylist(keys, errors=None):
    """ transform a list of gpg key URLs into a list of tuples of
    (filename, content), which is what the Pulp repoapi calls expect """
    if errors is None:
        errors = []
    keylist = dict()
    for keyurl in keys:
        if not keyurl:
            continue
        key = os.path.basename(keyurl)
        try:
            keylist[key] = urlopen(keyurl).read()
        except IOError, err:
            errors.append("Could not download GPG key from %s: %s" %
                          (keyurl, err))
    # keylist is a dict of key-name: key-content.  we transform this
    # to a list of tuples, which is what RepositoryAPI.addkeys()
    # expects.
    return keylist.items()

def set_gpgkeys(repo, keys, request=None, errors=None):
    repoapi = RepositoryAPI()
    if errors is None:
        errors = []
    to_remove = [k for k, kurl in repo['keys'].items() if k not in keys]
    try:
        repoapi.rmkeys(repo['id'], to_remove)
        if request:
            messages.debug(request,
                           "Removed GPG keys %s from %s" %
                           (to_remove, repo['name']))
    except ServerRequestError, err:
        errors.append("Could not remove GPG keys (%s) from %s: %s" %
                      (to_remove, repo['name'], err[1]))
    
    keylist = [(fn, key)
               for fn, key in get_keylist(keys, errors=errors)
               if key not in repo['keys']]
    if keylist:
        try:
            repoapi.addkeys(repo['id'], keylist)
            if request:
                messages.debug(request,
                               "Added GPG keys (%s) to %s" %
                               ([fn for fn, key in keylist], repo['name']))
        except ServerRequestError, err:
            errors.append("Could not add GPG keys (%s) to %s: %s" %
                          ([fn for fn, key in keylist], repo['name'], err[1]))

    reload_repo(repo['id'])
    if errors:
        if request:
            for err in errors:
                messages.error(request, err)
            return False
        else:
            return errors
    else:
        return True

def sync_foreground(repo_id):
    taskapi = TaskAPI()
    repoapi = RepositoryAPI()
    running = repoapi.running_task(repoapi.sync_list(repo_id))
    if running is not None:
        raise Exception("Sync for repository %s already in progress" % repo_id)
    
    task = repoapi.sync(repo_id)
    while not task_end(task):
        time.sleep(1)
        task = taskapi.info(task['id'])

    if not task_succeeded(task):
        if task['exception'] and task['traceback']:
            raise Exception(task['traceback'][-1])
        elif task['exception']:
            raise Exception("Unknown sync error: %s" % task['exception'])
        else:
            raise Exception("Unknown sync error")
            
    return task

def rebalance_sync_schedule(errors=None):
    def by_package_count(repo1, repo2):
        """ sort a list of repositories by package_count """
        if repo1['package_count'] > repo2['package_count']:
            return 1
        elif repo1['package_count'] < repo2['package_count']:
            return -1
        else:
            return 0

    repos = get_repos()

    # get a list of sync frequencies
    syncgroups = dict()  # dict of sync time -> [groups]
    default = None
    for ckey, sync in config.list(filter=dict(name__startswith="sync_frequency_")).items():
        group = ckey.replace("sync_frequency_", "")
        if sync is None:
            logger.error("Sync frequency for %s is None, skipping" % group)
            continue
        synctime = 60 * 60 * int(sync)
        if "group" == "default":
            default = synctime
        else:
            try:
                syncgroups[synctime].append(group)
            except KeyError:
                syncgroups[synctime] = [group]

    # divide the repos up by sync time and sort them by package count
    # ascending.  this a) puts the repos in the same order every day
    # so that repos don't go ($synctime * 2 - 1) hours without being
    # synced; and b) does the heavy lifting early in the morning
    cycles = dict() # dict of repo -> sync time
    for repo in repos.values():
        cycles[repo['id']] = default
        for synctime, groups in syncgroups.items():
            if (set(groups) & set(repo['groupid']) and
                (cycles[repo['id']] is None or
                 synctime > cycles[repo['id']])):
                cycles[repo['id']] = synctime

    # finally, build a dict of sync time -> [repos]
    syncs = dict()
    for repoid, synctime in cycles.items():
        if synctime is None:
            continue
        try:
            syncs[synctime].append(repos[repoid])
        except KeyError:
            syncs[synctime] = [repos[repoid]]

    for synctime, syncrepos in syncs.items():
        syncrepos.sort(by_package_count)
        syncrepos.reverse()

        # we count the total number of packages in all repos, and
        # divide them evenly amongst the timespan allotted.  It's
        # worth noting that we count clones just the same as we count
        # "regular" repos, because it's createrepo, not the sync, that
        # really takes a lot of time and memory.
        pkgs = 0
        for repo in syncrepos:
            if repo['package_count'] < 10:
                # we still have to run createrepo even if there are
                # very few (or no!) packages, so count very small
                # repos as 10 packages
                pkgs += 10
            else:
                pkgs += repo['package_count']
    
        try:
            pkgtime = float(synctime) / pkgs
        except ZeroDivisionError:
            pkgtime = 1
            logger.debug("Allowing %s seconds per package" % pkgtime)

        # find tomorrow morning at 12:00 am
        tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)
        start = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day)

        if errors is None:
            errors = []

        for repo in syncrepos:
            iso8601_start = format_iso8601_datetime(start)
            iso8601_interval = \
                format_iso8601_interval(datetime.timedelta(seconds=synctime))
            logger.debug("Scheduling %s to start at %s, sync every %s" %
                         (repo['id'], iso8601_start, iso8601_interval))
            schedule = parse_interval_schedule(iso8601_interval,
                                               iso8601_start,
                                               None)

            try:
                set_schedule(repo, schedule)
            except ServerRequestError, err:
                errors.append("Could not set schedule for %s: %s" %
                              (repo['id'], err[1]))
            
            start += datetime.timedelta(seconds=int(pkgtime *
                                                    repo['package_count']))
    return not errors
