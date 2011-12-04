""" filter functions """

import logging
import threading
from pulp.client.api.filter import FilterAPI
from sponge.utils import get_pulp_server, get_config

logger = logging.getLogger(__name__)

def list_filters():
    filters = getattr(threading.local(), "filters", None)
    if filters is None:
        filterapi = FilterAPI()
        filters = dict([(f['id'], f) for f in filterapi.filters()])
        setattr(threading.local(), "filters", filters)
    return filters

def get_filter(fid):
    return list_filters()[fid]
