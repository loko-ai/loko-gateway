import ipaddress
import socket

import aiodns
from aiohttp import ClientSession
from aiohttp import ClientTimeout
from ds4biz_commons.utils.config_utils import guess_convert

resolver = aiodns.DNSResolver()

class AsyncRequest:
    def __init__(self, url, method='GET', accept='json', eval=True, **kwargs):
        self.url = url
        self.method = method
        self.accept = accept
        self.eval = eval
        self.kwargs = kwargs


async def request(url, method="GET", accept="json", **kwargs):
    async with ClientSession(timeout=ClientTimeout(total=60*5)) as session:
        resp = await session.request(method=method, url=url,**kwargs)
        if resp.status!=200:
            raise Exception((await resp.text()).strip('"'))
        if accept == "json":
            if resp.headers.get('Transfer-Encoding') == 'chunked':
                resp = await resp.content.read()
                return guess_convert(resp.decode())
            return await resp.json()
        if accept == "file":
            return await resp.read()
        resp = await resp.text()
        return guess_convert(resp)
    # except Exception as inst:
    #     logging.exception(inst)


async def other_hosts(mask="255.255.255.0"):
    try:
        ips = await resolver.gethostbyname(socket.gethostname(), socket.AF_INET)
        ip = ips.addresses[0]
        if not ip.startswith("127."):
            nt = ipaddress.IPv4Network('{}/{}'.format(ip, mask), strict=False)
            for el in nt.hosts():
                if el != ip:
                    yield el
    except Exception as e:
        print('ex:', e)
