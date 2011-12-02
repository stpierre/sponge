""" role functions """

import logging
import threading
from pulp.client.api.role import RoleAPI
from sponge.utils import get_pulp_server, get_config

logger = logging.getLogger(__name__)

def list_roles():
    roles = getattr(threading.local(), "roles", None)
    if roles is None:
        roleapi = RoleAPI()
        roles = dict([(r, roleapi.info(r)) for r in roleapi.list()])
        setattr(threading.local(), "roles", roles)
    return roles

def get_role(rid):
    return list_roles()[rid]
