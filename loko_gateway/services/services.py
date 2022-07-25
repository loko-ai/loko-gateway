import asyncio
import traceback
from collections import defaultdict
from os import path
from urllib.parse import urlparse

import socketio
from aiohttp import ClientSession, ClientTimeout
from sanic import Sanic, response
from sanic.exceptions import NotFound, SanicException
from sanic.response import json as sjson
from sanic_cors import CORS
from sanic_openapi import swagger_blueprint, doc

from loko_gateway.business.scan import check
from loko_gateway.config import app_config
from loko_gateway.config.app_config import PORT, AUTO_RELOAD, SERVICE_DEBUG, ASYNC_REQUEST_TIMEOUT, SESSION_TIMEOUT, \
    AUTOSCAN, USERS_DAO, HOSTS, HOSTS_FILE
from loko_gateway.dao.hosts_dao import HostsDAO
from loko_gateway.model.listeners import Observable, UploadLimit
from loko_gateway.utils.async_request import other_hosts
from loko_gateway.utils.path_utils import to_relative

swagger_blueprint.url_prefix = "/api"

appname = "agateway"
app = Sanic(appname)

hostsdao = HostsDAO(hosts_path=HOSTS_FILE)
hostsdao.save(HOSTS)

CORS(app, expose_headers=["Range"])
app.config["API_TITLE"] = appname
app.config["KEEP_ALIVE"] = False
app.config["RESPONSE_TIMEOUT"] = 60 * 10
app.config.REQUEST_MAX_SIZE = 10000000000

app.blueprint(swagger_blueprint)
app.config["API_SCHEMES"] = ["http", "https"]

rules = {}

"""if rules is None:
    with open(RULES_FILE) as rf:
        rules = json.load(rf)"""


async def islice(it, m):
    count = 0
    async for el in it:
        if count < m:
            yield el
            count += 1
        else:
            break


oldpaths = None


async def scan(ports=(8080,), max_hosts=30, autoscan=True):
    global oldpaths
    oldscans = defaultdict(list)
    t = 3

    hosts = hostsdao.all().values()

    while True:
        scans = []
        if autoscan:
            scans += [check("127.0.0.1", port) for port in ports if port != PORT]
            scans += [check(ip, 8080) async for ip in islice(other_hosts(), max_hosts)]

        resp = defaultdict(list)
        for x in await asyncio.gather(*scans):
            if x and x.get("type") != appname:
                resp[x['type']].append(x)

        if resp != oldscans:
            rules.clear()
            oldscans = resp
            if autoscan:
                for type, x in resp.items():
                    for i, service in enumerate(x):
                        base_url = "{}:{}/{}".format(service['ip'], service['port'], service['path'])
                        try:
                            info_url = 'http://' + base_url.strip('/') + '/info'
                            respp = await app.aiohttp_session.get(url=info_url)
                            name = (await respp.json())['label']
                        except Exception:
                            name = type if i == 0 else type + "_" + str(i + 1)

                        rules[name] = service, base_url
            if hosts:
                for type, x in resp.items():

                    for service in x:
                        print(type, service)
                        if service['mount']:
                            rules[service['mount']] = service, "{}:{}/{}".format(service['ip'], service['port'],
                                                                                 service['path'])

            t = 3
        else:
            t += 5
            t = min(60, t)

        if hasattr(swagger_blueprint, "_spec"):
            spec = swagger_blueprint._spec
            if not oldpaths:
                oldpaths = dict(spec.paths)
            spec.paths = dict(oldpaths)
            for k, v in rules.items():
                bp = v[0]['swagger'].basePath or "/"
                if bp != "/":
                    offs = 1
                else:
                    offs = len(v[0]['path']) + 1
                for p, cont in v[0]['swagger'].paths.items():
                    # print(p, )
                    spec.paths[path.join("/", k, to_relative(p[offs:]))] = cont

        print("Next scan in %d seconds " % t)
        await asyncio.sleep(t)


@app.post("/hosts")
@doc.consumes(doc.JsonBody(fields=dict()), location="body", required=True)
async def add_hosts(request):
    hostsdao.save(request.json)
    return sjson('OK')


@app.get("/hosts")
async def get_hosts(request):
    return sjson(list(hostsdao.all().values()))


@app.delete("/hosts")
@doc.consumes(doc.String(name="name"), required=True)
async def delete_hosts(request):
    name = request.args.get('name')
    hostsdao.delete(name)
    return sjson('OK')


@app.get("/users")
async def usernames(request):
    ret = []
    for x in USERS_DAO.all():
        m = x.__dict__
        del m["password"]
        ret.append(m)
    return sjson(ret)


@app.listener("before_server_start")
async def m(app, loop):
    loop.create_task(scan(ports=list(range(8080, 8090)) + [8888], autoscan=AUTOSCAN))
    total_timeout = ClientTimeout(total=SESSION_TIMEOUT)
    app.ctx.aiohttp_session = ClientSession(loop=loop, timeout=total_timeout)


@app.listener('before_server_stop')
def term(app, loop):
    exit(0)


@app.get("/services")
async def get_services(request):
    return sjson(list(rules.keys()))


@app.get("/rules")
async def get_rules(request):
    return sjson(rules)


@app.get("/services/<type>")
async def get_service_by_type(request, type):
    return sjson([k for k, x in rules.items() if x[0]['type'] == type])


@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@doc.exclude(True)
async def main(request, path):
    headers = dict(request.headers)

    temp = urlparse(path)
    name, *rest = temp.path.split("/")
    params = {k: request.args.get(k) for k in request.args}
    if name in rules:
        _, host = rules[name]
        host = host.strip("/")
        print("host:", host, "rest:", rest, "temp:", temp.query)
        if temp.query:
            url = "http://{}/{}?{}".format(host, "/".join(rest), temp.query)
        else:
            url = "http://{}/{}".format(host, "/".join(rest))
        print("URL", url)
        resp = await app.aiohttp_session.request(method=request.method, url=url, data=request.body, headers=headers,
                                                 params=params, timeout=ASYNC_REQUEST_TIMEOUT)
        ct = resp.headers.get('content-type')
        kws = ['allow-origin']
        headers = {k: v for k, v in dict(resp.headers).items() if not any([el in k.lower() for el in kws])}
        print(resp.headers)
        print(headers)
        response.headers = headers

        if resp.headers.get('Transfer-Encoding') == 'chunked':

            def streaming_fn(resp):
                async def ret(response):
                    buffer = b""
                    async for data, end_of_http_chunk in resp.content.iter_chunks():
                        buffer += data
                        if end_of_http_chunk:
                            await response.write(buffer)
                            print('line::', end_of_http_chunk, buffer)
                            buffer = b""
                    resp.close()

                return ret

            return response.stream(streaming_fn(resp))
        # if ct == 'application/json' and not "Range" in headers:
        #     return sjson(await resp.json(), headers = headers)
        # if ct == 'plain/text':
        #     return sjson(await resp.text(), headers = headers)
        return response.raw(await resp.content.read(), content_type=ct, headers=headers, status=resp.status)
    else:
        raise SanicException(status_code=404)


sio = socketio.AsyncServer(async_mode='sanic', cors_allowed_origins=[])
sio.attach(app)


@app.post("/emit")
@doc.consumes(doc.JsonBody(dict(event_name=str, content=dict)), location="body")
async def send(request) -> str:
    """Send a message through websocket
        Examples
        --------
        data = {"event_name": "topic_name", "content" : {"msg" : "string"}}

    <font color="#800000"><b>Emit service send a message through websocket to a websocker server, to check the job's status use GET /jobs/{name}</b></font>
     """
    event = request.json
    await sio.emit(event["event_name"], event["content"])
    return sjson("OK")


@app.exception(Exception)
async def manage_exception(request, exception):
    if isinstance(exception, NotFound):
        return sjson(str(exception), status=404)
    print(traceback.format_exc())
    return sjson(str(exception), status=500)


@sio.event
async def messages(sid, data):
    print('message received with ', data)
    await sio.emit('messages', data)


@sio.event
async def message(sid, data):
    print('message received with ', data)
    await sio.emit('message', data)


@sio.event
async def project(sid, data):
    print('message received with ', data)
    await sio.emit('project', data)


@sio.event
async def system(sid, data):
    print('message received with ', data)
    await sio.emit('system', data)


@sio.event
async def flows(sid, data):
    print('message received with ', data)
    await sio.emit('flows', data)


@sio.event
async def animation(sid, data):
    print('message received with ', data)
    await sio.emit('animation', data)


@sio.event
async def info(sid, data):
    print('message received with ', data)
    await sio.emit('info', data)

#creo l'observable di riferimento al quale aggiungere le callback
o = Observable()
CONFIG = {"LIMIT": 200, "GATEWAY": "http://gateway.livetech.site"}
ul = UploadLimit(CONFIG['LIMIT'])
#callback legata al cambiamento del valore di "LIMIT" nel config che richiama il metodo set_limit della classe uploadlimit
o.add_observer("LIMIT", lambda data: ul.set_limit(data['LIMIT']))
# o.add_observer("GATEWAY", lambda data: ul.set_limit(data['GATEWAY']))
#su update del gateway non fa niente in questo caso
#http://localhost:8080/config

@app.get("/config")
async def get_config(request):
    return sjson(CONFIG)

# curl -X PUT "http://localhost:8080/config" -H "Content-type: application/json" -d'{"LIMIT":300}'
@app.put("/config")
@doc.consumes(doc.JsonBody(fields=dict(LIMIT=int)), location="body", required=True)
async def set_config(request):
    body = request.json
    print(body)
    CONFIG.update(request.json)
    for key in body.keys():
        #lancia una notifica per ogni chiave cambiata
        o.notify(key, CONFIG)
    return sjson("OK")

app.run("0.0.0.0", port=PORT, debug=SERVICE_DEBUG, auto_reload=AUTO_RELOAD)
