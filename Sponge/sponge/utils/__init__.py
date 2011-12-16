import os
import logging
from pulp.client.api import server
from pulp.client.api.user import UserAPI
from pulp.client.consumer.config import ConsumerConfig
from pulp.common.bundle import Bundle
from django.conf import settings
from djcelery.models import PeriodicTask, IntervalSchedule

logger = logging.getLogger(__name__)

class SpongeBundle(Bundle):
    """ A bundle that stores its cert in a temp file """
    def __init__(self, user):
        path = str(os.path.join(getattr(settings,
                                        'PULP_CERTIFICATE_PATH',
                                        'certs'),
                                "%s.crt" % user))
        Bundle.__init__(self, path)


def get_pulp_server(user=None, new=False):
    """ set up a pulp client server instance """
    if new or not isinstance(server.active_server, server.Server):
        config = ConsumerConfig()
        pulpserver = server.PulpServer(config.server['host'],
                                       int(config.server['port']),
                                       config.server['scheme'],
                                       config.server['path'])
        server.set_active_server(pulpserver)

    if user:
        bundle = SpongeBundle(user)
        if os.path.exists(bundle.crtpath()):
            server.active_server.set_ssl_credentials(bundle.crtpath())
        else:
            raise IOError("No Pulp certificate found for %s at %s" %
                          (user, bundle.crtpath()))

        # make a quick and easy API call to verify that the session is
        # still active
        userapi = UserAPI()
        userapi.user(user)

    return server.active_server

def get_config():
    return ConsumerConfig()

def set_rebalance_schedule(errors=None):
    syncs = config.list(filter=dict(name__startswith="sync_frequency_"))
    
    schedule = \
        IntervalSchedule.objects.create(every=max([int(v)
                                                   for v in syncs.values()]),
                                        period="hours")
    PeriodicTask.objects.create(name="rebalance_sync_schedule",
                                task="sponge.tasks.RebalanceSyncSchedule")
    
