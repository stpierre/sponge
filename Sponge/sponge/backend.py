import os
import logging
import traceback
from django.contrib.auth.models import User
from sponge.utils import get_pulp_server, SpongeBundle, user as user_utils
from pulp.client.api.user import UserAPI
from pulp.client.api import server

logger = logging.getLogger(__name__)

class PulpAuthentication():
    """ Authenticates against the Pulp server in the Pulp client
    config (/etc/pulp/client.conf) """
    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False
    
    def __init__(self):
        self.server = get_pulp_server()
        self.userapi = UserAPI()
    
    def authenticate(self, username, password=None):
        """ authenticate a user """
        try:
            self.server.set_basic_auth_credentials(username, password)
            logging.info("Successfully logged in with password")
            cert = self.userapi.admin_certificate()
            bundle = SpongeBundle(username)
            bundle.write(cert)
            self.server = get_pulp_server(new=True)
            self.server.set_ssl_credentials(bundle.crtpath())
            udata = self.userapi.user(username)
            logger.info("%s logged in successfully" % username)
        except server.ServerRequestError, err:
            logger.warning("Login failure for %s: %s" % (username, err[1]))
            return None
        except Exception, err:
            logger.warning(traceback.format_exc())
            return None

        # we got the user data above with a direct UserAPI call so
        # that we could catch errors and tell if the login was
        # successful.  now let's get better data using user_utils
        udata = user_utils.get_user(username)

        user, created = User.objects.get_or_create(username=username)
        if created:
            logger.info("Created new user object for %s", username)
            user.set_unusable_password()
        user.is_superuser = user_utils.is_superuser(username)
        user.first_name = udata['name'].split()[0]
        user.last_name = " ".join(udata['name'].split()[1:])
        user.save()
        
        return user

    def get_user(self, user_id):
        """ get a user object representing a user """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

