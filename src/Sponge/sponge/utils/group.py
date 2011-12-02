""" filter functions """

import logging
from sponge.utils import repo as repo_utils

logger = logging.getLogger(__name__)

def get_groups():
    rv = set()
    for repo in repo_utils.get_repos().values():
        rv.update(repo['groupid'])
    return list(rv)
    
