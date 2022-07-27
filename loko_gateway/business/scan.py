import asyncio

from aiohttp import ClientSession, ClientTimeout
from ds4biz_commons.utils.dict_utils import ObjectDict

from loko_gateway.utils.path_utils import common_prefix


async def check(ip, port, mount=None):
    timeout = ClientTimeout(sock_connect=1.0, sock_read=3.0)
    try:
        async with ClientSession(timeout=timeout) as session:
            url = "http://{}:{}/swagger.json".format(ip, port)
            resp = await session.get(url)
            if resp.status == 404:
                url = "http://{}:{}/api/swagger.json".format(ip, port)
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
            return dict(ip=ip, port=port, type=resp.info.title, path=fpath, swagger=resp, mount=mount)

    except Exception as inst:
        return None


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check("0.0.0.0", 8082))
