import json
import os.path

from ds4biz_commons.utils.dict_utils import ObjectDict
from ds4biz_commons.utils.requests_utils import URLRequest
from tinydb import TinyDB, Query

from loko_gateway.model.users import User
from loko_gateway.utils.exceptions import error_handler
from loko_gateway.utils.resources_utils import get_resource


class UserDAO:
    def user_by_username(self, username):
        pass


class IMUserDAO(UserDAO):
    def __init__(self, *users):
        self.users = {}
        self.add_users(*users)

    def add_users(self, *users):
        for u in users:
            self.users[u.username] = u

    def user_by_username(self, username) -> User:
        return self.users.get(username)

    def user_by_email(self, email):
        for u in self.all():
            if u.email == email:
                return u

    def usernames(self):
        return list(self.users)

    def all(self):
        for k, v in self.users.items():
            yield v

    def exist(self, username):
        return username in self.usernames()

    def insert(self, user: User):
        self.users[user.username] = user

    def delete(self, username):
        if self.exist(username):
            del self.users[username]
        else:
            raise Exception("User not found")


class TinyUDAO(UserDAO):

    def __init__(self, users=[], fname=None, tname=None):
        self.tname = tname or "users"
        self.fname = fname or get_resource("users/users.json")
        self.load()
        self.Q = Query()
        self.add_users(users)

    def load(self):
        if not os.path.exists(self.fname):
            os.makedirs(os.path.split(self.fname)[0], exist_ok=True)
            with open(self.fname, "w") as f:
                json.dump({}, f, indent=2)

        self.db = TinyDB(self.fname)
        self.tab = self.db.table(self.tname)


    def add_users(self, users):
        for u in users:
            if not self.exist(u.username):
                self.insert(u)

    def user_by_username(self, username):
        self.load()
        for el in self.tab.search(self.Q.username == username):
            return User(**el)

    def user_by_email(self, email):
        self.load()
        for el in self.tab.search(self.Q.email == email):
            return User(**el)

    def obj_exist(self, obj):
        self.load()
        d = list(obj.items())
        return bool(self.tab.search(self.Q[d[0][0]] == d[0][1]))

    def exist(self, username):
        self.load()
        return bool(self.tab.search(self.Q.username == username))

    def insert(self, doc: User):
        if not list(self.tab.search(self.Q.username == doc.username)):
            self.tab.insert(doc.__dict__)
        else:
            self.update(doc)

    def update(self, doc: User):
        self.load()
        self.tab.update(doc.__dict__, self.Q.username == doc.username)

    def all(self):
        self.load()
        for el in iter(self.tab):
            yield User(**el)

    def delete(self, username):
        self.tab.remove(self.Q.username == username)


class RESTUDAO(UserDAO):

    def __init__(self, url, username, password):
        self.url = URLRequest(f"{url}")
        self.username = username
        self.password = password

    @error_handler
    def insert(self, doc: User):
        resp = self.url.auth.post(json=dict(username=self.username, password=self.password))
        self.bearer = f"Bearer {resp.get('access_token')}"

        resp = self.url.users.post(json=doc.__dict__, headers=dict(authorization=self.bearer))
        return resp

    @error_handler
    def get_by_id(self, id):
        resp = self.url.auth.post(json=dict(username=self.username, password=self.password))
        self.bearer = f"Bearer {resp.get('access_token')}"

        resp = self.url.users[id].get(headers=dict(authorization=self.bearer))
        resp = ObjectDict(resp)
        return resp

    @error_handler
    def all(self):
        resp = self.url.auth.post(json=dict(username=self.username, password=self.password))
        self.bearer = f"Bearer {resp.get('access_token')}"

        resp = self.url.users.get(headers=dict(authorization=self.bearer))
        for el in resp:
            yield el

    @error_handler
    def exist(self, email):
        resp = self.url.auth.post(json=dict(username=self.username, password=self.password))
        self.bearer = f"Bearer {resp.get('access_token')}"

        resp = self.url.users.exist.post(json=dict(email=email), headers=dict(authorization=self.bearer))
        return resp

    @error_handler
    def add_users(self, *users):
        raise ("not Implemented")

    @error_handler
    def user_by_username(self, username):
        resp = self.url.auth.post(json=dict(username=self.username, password=self.password))
        self.bearer = f"Bearer {resp.get('access_token')}"

        resp = self.url.users.username[username].get(headers=dict(authorization=self.bearer))
        resp = ObjectDict(resp)
        return resp

    @error_handler
    def user_by_email(self, email):
        resp = self.url.auth.post(json=dict(username=self.username, password=self.password))
        self.bearer = f"Bearer {resp.get('access_token')}"

        resp = self.url.users.email[email].get(headers=dict(authorization=self.bearer))
        resp = ObjectDict(resp)
        return resp

    @error_handler
    def update(self, doc: User):
        resp = self.url.auth.post(json=dict(username=self.username, password=self.password))
        self.bearer = f"Bearer {resp.get('access_token')}"

        self.mdao.update(doc.id, doc.__dict__)

    @error_handler
    def delete(self, username):
        resp = self.url.users[username].delete(headers=dict(authorization=self.bearer))
        return resp
