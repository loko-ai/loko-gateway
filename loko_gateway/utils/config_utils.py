from loko_gateway.config import app_config

CONFIG = {k: v for k, v in app_config.__dict__.items() if k.isupper() and not "DAO" in k}
