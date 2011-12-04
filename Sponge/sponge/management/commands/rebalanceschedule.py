import logging
from sponge.utils import get_pulp_server, SpongeBundle
from sponge.utils import config as SpongeConfig
from sponge.utils.repo import rebalance_sync_schedule
from django.core.management.base import BaseCommand, CommandError
from pulp.client.api import server
from pulp.client.api.repository import RepositoryAPI
from pulp.client.api.user import UserAPI
from pulp.client.consumer.config import ConsumerConfig

class PulpLoginError(Exception):
    pass


class Command(BaseCommand):
    help = 'Rebalances the Pulp sync schedules'

    def setup_pulp(self):
        """ instantiate pulp server object and log in """
        config = ConsumerConfig()
        userapi = UserAPI()
        serveropts = config.server
        pulpserver = server.PulpServer(serveropts['host'],
                                       int(serveropts['port']),
                                       serveropts['scheme'],
                                       serveropts['path'])
        server.set_active_server(pulpserver)

        bundle = SpongeBundle(SpongeConfig.get("scheduler_username"))
        try:
            server.active_server.set_basic_auth_credentials(SpongeConfig.get("scheduler_username"),
                                                            SpongeConfig.get("scheduler_password"))
            crt = userapi.admin_certificate()
            bundle.write(crt)
        except server.ServerRequestError, err:
            self.stderr.write("Could not authenticate to Pulp: %s\n" % err[1])
            self.stderr.write("Ensure that the scheduler username and password are set properly in Sponge\n")
            raise SystemExit(1)

    def handle(self, *args, **options):
        errors = []
        self.setup_pulp()
        if rebalance_sync_schedule(errors=errors):
            self.stdout.write("Successfully rebalanced sync schedules\n")
        else:
            self.stderr.write("Encountered errors while rebalancing sync schedules:\n")
            self.stderr.write("\n".join(errors))
