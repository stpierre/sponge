""" user functions """

import logging
import threading
from pulp.client.api.user import UserAPI
from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.server import ServerRequestError
from sponge.utils import get_pulp_server, get_config

logger = logging.getLogger(__name__)

def list_users():
    users = getattr(threading.local(), "users", None)
    if users is None:
        users = dict()
        userapi = UserAPI()
        consumerapi = ConsumerAPI()
        for user in userapi.users():
            if user['roles'] == ['consumer-users']:
                # this might be a consumer, but the only way to know
                # for sure is to try to load it as a consumer
                try:
                    consumerapi.consumer(user['login'])
                    # yes, this is a consumer.  ignore it.
                    continue
                except ServerRequestError:
                    pass

            if 'name' not in user or not user['name']:
                user['name'] = user['login']
            elif 'name' in user and isinstance(user['name'], list):
                user['name'] = user['name'][0]
            users[user['login']] = user
        setattr(threading.local(), "users", users)
    return users

def get_user(login):
    return list_users()[login]

def is_superuser(login):
    return "super-users" in get_user(login)['roles']
