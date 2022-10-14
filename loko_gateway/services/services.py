import asyncio
import traceback
from os import path
from urllib.parse import urlparse

import socketio
from aiohttp import ClientSession, ClientTimeout
from sanic import Sanic
from sanic.exceptions import NotFound, SanicException
from sanic.response import json as sjson, raw
from sanic_cors import CORS
from sanic_openapi import swagger_blueprint, doc

from loko_gateway.config.app_config import PORT, AUTO_RELOAD, SERVICE_DEBUG, ASYNC_REQUEST_TIMEOUT, SESSION_TIMEOUT, \
    RULES_DAO, RULES
from loko_gateway.utils.config_utils import CONFIG
from loko_gateway.utils.path_utils import to_relative

swagger_blueprint.url_prefix = "/api"

appname = "agateway"
app = Sanic(appname)
sio = socketio.AsyncServer(async_mode='sanic', cors_allowed_origins=[])
sio.attach(app)

CORS(app, expose_headers=["Range"])
app.config["API_TITLE"] = appname
app.config["KEEP_ALIVE"] = False
app.config["RESPONSE_TIMEOUT"] = 60 * 10
app.config.REQUEST_MAX_SIZE = 10000000000

app.blueprint(swagger_blueprint)
app.config["API_SCHEMES"] = ["http", "https"]


async def islice(it, m):
    count = 0
    async for el in it:
        if count < m:
            yield el
            count += 1
        else:
            break


oldpaths = None


def update_swagger():
    if hasattr(swagger_blueprint, "_spec"):
        spec = swagger_blueprint._spec
        for rule in RULES_DAO.all():
            md = rule.metadata
            bp = md["swagger"].basePath or "/"
            if bp != "/":
                offs = 1
            else:
                offs = len(['path']) + 1
            for p, cont in md['swagger'].paths.items():
                spec.paths[path.join("/", rule.name, to_relative(p[offs:]))] = cont


# async def scan(ports=(8080,), max_hosts=30):
#     global oldpaths
#     oldscans = defaultdict(list)
#     t = 3
#
#     l = "127.0.0.1"
#
#     while True:
#
#         scans = [check(l, port) for port in ports if port != PORT]
#
#         scans.extend([check(ip, 8080) async for ip in islice(other_hosts(), max_hosts)])
#         resp = defaultdict(list)
#         for x in await asyncio.gather(*scans):
#             if x and x.get("type") != appname:
#                 resp[x['type']].append(x)
#
#         if resp != oldscans:
#             # RULES.clear()
#             oldscans = resp
#             for type, x in resp.items():
#                 for i, service in enumerate(x):
#                     base_url = "{}:{}/{}".format(service['ip'], service['port'], service['path'])
#                     try:
#                         info_url = 'http://' + base_url.strip('/') + '/info'
#                         resp = await app.ctx.aiohttp_session.get(url=info_url)
#                         name = (await resp.json())['label']
#                     except Exception:
#                         name = type if i == 0 else type + "_" + str(i + 1)
#
#                     RULES[name] = service, base_url
#
#             t = 3
#         else:
#             t += 5
#             t = min(60, t)
#
#
#         print("Next scan in %d seconds " % t)
#         await asyncio.sleep(t)


# async def manual_scan():
#     for i in range(5):
#         print("Scan", i)
#         for host in HOSTS:
#             print("Host", host)
#         scans = [check(host, port, mount) for (mount, host, port) in HOSTS]
#
#         resp = defaultdict(list)
#         for x in await asyncio.gather(*scans):
#             if x and x.get("type") != appname:
#                 resp[x['type']].append(x)
#
#         for type, x in resp.items():
#
#             for service in x:
#                 print(type, service)
#                 RULES[service['mount']] = service, "{}:{}/{}".format(service['ip'], service['port'], service['path'])
#         if hasattr(swagger_blueprint, "_spec"):
#             spec = swagger_blueprint._spec
#             # spec.paths = {}
#             for k, v in RULES.items():
#                 bp = v[0]['swagger'].basePath or "/"
#                 if bp != "/":
#                     offs = 1
#                 else:
#                     offs = len(v[0]['path']) + 1
#                 for p, cont in v[0]['swagger'].paths.items():
#                     # print(p, )
#                     spec.paths[path.join("/", k, to_relative(p[offs:]))] = cont
#         await  asyncio.sleep(5)


# @app.post("/hosts")
# @doc.consumes(doc.JsonBody(fields=dict()), location="body", required=True)
# async def update_hosts(request):
#     hostsdao.save(request.json)
#     return sjson('OK')
#
#
# @app.get("/hosts")
# async def get_hosts(request):
#     return sjson(list(hostsdao.all().values()))
#
#
# @app.delete("/hosts")
# @doc.consumes(doc.String(name="name"), required=True)
# async def delete_hosts(request):
#     name = request.args.get('name')
#     hostsdao.delete(name)
#     return sjson('OK')


SCAN_TASK = None
LOOP = None


async def scan():
    temp = list(RULES)
    while temp:
        print("Giro", temp)
        try:
            for r in list(temp):
                try:
                    print("Aggancio", r)
                    await RULES_DAO.mount(r["name"], r["host"], r["port"], r["type"])
                    temp.remove(r)
                except Exception as inst:
                    print(r, inst)
            print("Sleeping")
            await asyncio.sleep(3)
            print("Ho dormito")
        except Exception as e2:
            print("Global", e2)


@app.listener("after_server_start")
async def m(app, loop):
    global LOOP
    global SCAN_TASK
    total_timeout = ClientTimeout(total=SESSION_TIMEOUT)
    app.ctx.aiohttp_session = ClientSession(loop=loop, timeout=total_timeout)
    LOOP = loop
    loop.create_task(scan())

    # if CONFIG["AUTOSCAN"]:
    #     SCAN_TASK = loop.create_task(scan(ports=list(range(8080, 8090)) + [8888]))
    # else:
    #     SCAN_TASK = loop.create_task(manual_scan())


@app.listener('before_server_stop')
def term(app, loop):
    exit(0)


@app.get("/services")
async def get_services(request):
    return sjson(list(RULES.keys()))


@app.get("/services/<type>")
async def get_service_by_type(request, type):
    return sjson([x.name for x in RULES_DAO.all() if x.type == type])


@app.route("/routes/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@doc.exclude(True)
async def main(request, path):
    headers = dict(request.headers)
    temp = urlparse(path)
    name, *rest = temp.path.split("/")
    params = {k: request.args.get(k) for k in request.args}

    rule = RULES_DAO.get(name)
    if rule:
        if temp.query:
            url = f"http://{rule.host}:{rule.port}{rule.base_path}/{'/'.join(rest)}?{temp.query}"
        else:
            url = f"http://{rule.host}:{rule.port}{rule.base_path}/{'/'.join(rest)}"
        resp = await app.ctx.aiohttp_session.request(method=request.method, url=url, data=request.body, headers=headers,
                                                     params=params, timeout=ASYNC_REQUEST_TIMEOUT)
        ct = resp.headers.get('content-type')
        kws = ['allow-origin']
        headers = {k: v for k, v in dict(resp.headers).items() if not any([el in k.lower() for el in kws])}

        if resp.headers.get('Transfer-Encoding') == 'chunked':
            rr = await request.respond(headers=headers)

            buffer = b""
            async for data, end_of_http_chunk in resp.content.iter_chunks():
                buffer += data
                if end_of_http_chunk:
                    await rr.send(buffer)
                    print('line::', end_of_http_chunk, buffer)
                    buffer = b""
            resp.close()

        # if ct == 'application/json' and not "Range" in headers:
        #     return sjson(await resp.json(), headers = headers)
        # if ct == 'plain/text':
        #     return sjson(await resp.text(), headers = headers)
        else:
            return raw(await resp.content.read(), content_type=ct, headers=headers, status=resp.status)
    else:
        raise SanicException(status_code=404)


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
    # print(traceback.format_exc())
    return sjson(str(exception), status=500)


@sio.event
async def messages(sid, data):
    print('message received with ', data)
    await sio.emit('messages', data)


@sio.event
async def message(sid, data):
    await sio.emit('message', data)


@sio.event
async def project(sid, data):
    await sio.emit('project', data)


@sio.event
async def system(sid, data):
    await sio.emit('system', data)


@sio.event
async def flows(sid, data):
    await sio.emit('flows', data)


@sio.event
async def animation(sid, data):
    await sio.emit('animation', data)


@sio.event
async def logs(sid, data):
    await sio.emit('logs', data)


@sio.event
async def events(sid, data):
    await sio.emit('events', data)


@sio.event
async def info(sid, data):
    await sio.emit('info', data)


async def set_autoscan(value):  # False
    global SCAN_TASK
    global LOOP

    CONFIG["AUTOSCAN"] = value

    if not value and SCAN_TASK:
        SCAN_TASK.cancel()
        SCAN_TASK = None
    else:  # value and not SCAN_TASK:
        SCAN_TASK = LOOP.create_task(scan(ports=list(range(8080, 8090)) + [8888]))


async def update_hosts(hosts):
    global SCAN_TASK
    global RULES
    print(RULES)
    RULES.clear()

    CONFIG["HOSTS"] = hosts

    if not hosts and SCAN_TASK:
        SCAN_TASK.cancel()
        SCAN_TASK = None
    else:  # value and not SCAN_TASK:
        SCAN_TASK = LOOP.create_task(scan(ports=list(range(8080, 8090)) + [8888]))


# # creo l'observable di riferimento al quale aggiungere le callback
# o = Observable()
# # CONFIG = {"LIMIT": 200, "GATEWAY": "http://gateway.livetech.site"}
# ul = UploadLimit(CONFIG['ASYNC_REQUEST_TIMEOUT'])
# # callback legata al cambiamento del valore di "LIMIT" nel config che richiama il metodo set_limit della classe uploadlimit
# o.add_observer("ASYNC_REQUEST_TIMEOUT", lambda data: ul.set_limit(data['ASYNC_REQUEST_TIMEOUT']))
# o.add_observer("AUTOSCAN", lambda data: set_autoscan(data['AUTOSCAN']))
# o.add_observer("HOSTS", lambda data: update_hosts(data['HOSTS']))


# o.add_observer("GATEWAY", lambda data: ul.set_limit(data['GATEWAY']))
# su update del gateway non fa niente in questo caso
# http://localhost:8080/config

@app.get("/config")
async def get_config(request):
    return sjson(CONFIG)


# curl -X PUT "http://localhost:8080/config" -H "Content-type: application/json" -d'{"LIMIT":300}'
@app.put("/config")
@doc.consumes(doc.JsonBody(), location="body", required=True)
async def set_config(request):
    body = request.json
    print(body)
    CONFIG.update(request.json)
    for key in body.keys():
        # lancia una notifica per ogni chiave cambiata
        await o.notify(key, CONFIG)
    return sjson("OK")


@app.get("/rules")
async def get_rules(request):
    return sjson([x.__dict__ for x in RULES_DAO.all()])


@app.post("/rules")
@doc.consumes(doc.JsonBody(fields=dict(name=str, host=str, port=int, scan=bool, type=str)), location="body",
              required=True)
async def register_rule(request):
    if request.json['scan']:
        print(request.json['scan'])
        await RULES_DAO.mount(**request.json)
    else:
        RULES_DAO.add_rule(**request.json)
    update_swagger()
    # await o.notify("HOSTS", CONFIG)
    # return sjson("OK")
    return sjson("OK")


@app.delete("/rules/<name>")
@doc.consumes(doc.String(name="name"), location="path", required=True)
async def deregister_rule(request, name):
    RULES_DAO.delete(name)
    # await o.notify("HOSTS", CONFIG)
    return sjson("OK")


app.run("0.0.0.0", port=PORT, access_log=False, debug=SERVICE_DEBUG, auto_reload=AUTO_RELOAD)
