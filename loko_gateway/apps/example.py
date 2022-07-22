from collections import defaultdict
from flask import Flask, jsonify, request
class Observable:
    def __init__(self):
        self.observers = defaultdict(list)
    def add_observer(self, event, obs):
        # gli observer sono funzioni che vengono lanciate quando si verifica un evento
        self.observers[event].append(obs)
    def notify(self, event, data):
        for obs in self.observers[event]:
            obs(data)
class UploadLimit:
    def __init__(self, limit):
        self.limit = limit
    def set_limit(self, limit):
        print("Refreshing/updating limit")
        self.limit = limit
#creo l'observable di riferimento al quale aggiungere le callback
o = Observable()
CONFIG = {"LIMIT": 200, "GATEWAY": "http://gateway.livetech.site"}
ul = UploadLimit(CONFIG['LIMIT'])
#callback legata al cambiamento del valore di "LIMIT" nel config che richiama il metodo set_limit della classe uploadlimit
o.add_observer("LIMIT", lambda data: ul.set_limit(data['LIMIT']))
#su update del gateway non fa niente in questo caso
app = Flask("config")
#http://localhost:8080/config
@app.route("/config")
def get_config():
    return jsonify(CONFIG)
# curl -X PUT "http://localhost:8080/config" -H "Content-type: application/json" -d'{"LIMIT":300}'
@app.route("/config", methods=["PUT"])
def set_config():
    body = request.json
    print(body)
    CONFIG.update(request.json)
    for key in body.keys():
        #lancia una notifica per ogni chiave cambiata
        o.notify(key, CONFIG)
    return jsonify("OK")
app.run("0.0.0.0", port=8080, debug=True)