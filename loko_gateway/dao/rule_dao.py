from typing import Dict, List

from loko_gateway.model.rules import Rule
from aiohttp import ClientSession, ClientTimeout

from loko_gateway.utils.path_utils import common_prefix
from ds4biz_commons.utils.dict_utils import ObjectDict


class RuleDAO:

    def __init__(self, rules=None):
        self.rules = rules or {}

    async def mount(self, name, host, port):
        self.rules[name] = await self.__create_rule(name, host, port)


    def get(self, name: str) -> Rule:
        return self.rules.get(name)

    def all(self) -> List[Rule]:
        return self.rules.values()

    def delete(self, name):
        del self.rules[name]

    async def __create_rule(self, name, ip, port):
        timeout = ClientTimeout(sock_connect=1.0, sock_read=3.0)
        async with ClientSession(timeout=timeout) as session:
            url = f"http://{ip}:{port}/swagger.json"
            resp = await session.get(url)
            if resp.status == 404:
                url = f"http://{ip}:{port}/api/swagger.json"
                resp = await session.get(url)
            resp = ObjectDict(await resp.json())
            paths = []
            for k in resp.paths:
                splitted = [x for x in k.split("/") if x]
                paths.append(splitted)

            base = [x for x in (resp.get("basePath") or "/").split("/") if x]
            if len(paths) > 1:
                common = common_prefix(paths)
                fpath = "/".join(base + common)
            else:
                fpath = "/".join(base + paths[0][:-1])
            fpath = "/" + fpath
            return Rule(name=name, host=ip, port=port, type=resp.info.title, base_path=fpath,
                        swagger=resp)

if __name__ == '__main__':
    dao = RuleDAO()
    dao.mount("predictor", "localhost", 8081)
    print(dao.get("predictor").__dict__)
