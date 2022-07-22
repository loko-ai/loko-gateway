## request max size 500MB
import logging

from loko_gateway.dao.users_dao import TinyUDAO
from loko_gateway.model.users import User
from loko_gateway.utils.resources_utils import get_resource

ENV_SANIC_REQUEST_MAX_SIZE = 500000000
## request timeout 1h
ENV_SANIC_REQUEST_TIMEOUT = 3600
## response timeout 1h
ENV_SANIC_RESPONSE_TIMEOUT = 3600

import json
import os

from ds4biz_commons.utils.config_utils import EnvInit

e = EnvInit()
PORT = e.get("PORT", 8080)
AUTOSCAN = e.get("AUTOSCAN", True)
HOSTS = e.get("HOSTS", [])
HOSTS_FILE = get_resource("hosts/hosts.json")

if not AUTOSCAN and not os.path.isfile(HOSTS_FILE) and not HOSTS:
    raise Exception('No hosts found! Set AUTOSCAN to True or manually define HOSTS')

if not os.path.isfile(HOSTS_FILE):
    p = os.path.split(HOSTS_FILE)
    print(p)
    os.mkdir(p[0])
    with open(HOSTS_FILE, 'w') as f:
        json.dump([], f)

ASYNC_REQUEST_TIMEOUT = e.get("ASYNC_REQUEST_TIMEOUT", 60 * 15)
SESSION_TIMEOUT = e.get("SESSION_TIMEOUT", 60 * 60)
SOCKET_HOST = e.get("SOKET_HOST")
SOCKET_PORT = e.get("SOKET_PORT")

TOKEN_EXPIRATION = e.get("TOKEN_EXPIRATION", 7 * 24 * 60 * 60)

AUTO_RELOAD = e.AUTO_RELOAD or False
SERVICE_DEBUG = e.SERVICE_DEBUG or False

ASYNC_SESSION_TIMEOUT = e.ASYNC_SESSION_TIMEOUT or 5 * 60

def get_users():
    users = os.environ.get("USERS")
    ret = []
    if users:
        try:
            users = json.loads(users)
            for u in users:
                ret.append(User(**u))
            return ret
        except Exception as inst:
            logging.exception(inst)
            logging.error("Backoff to default users")
    else:
        return [User(id="admin",username="admin", password="admin", role="ADMIN", email="admin@admin.it"),
                User(id="local",username="user", password="user", role="USER", email="user@user.it")]

USERS_DAO = TinyUDAO(get_users())