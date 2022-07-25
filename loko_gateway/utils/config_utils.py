import json
from pprint import pprint

from loko_gateway.config import app_config
from loko_gateway.utils.resources_utils import get_resource

fname = get_resource(("config.json"))

CONFIG = {k: v for k, v in app_config.__dict__.items() if k.isupper() and not "DAO" in k}
pprint(CONFIG)

with open(fname, "w") as f:
    json.dump(CONFIG, f, indent=3)
