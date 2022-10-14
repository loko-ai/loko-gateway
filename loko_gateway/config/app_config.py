from ds4biz_commons.utils.config_utils import EnvInit

from loko_gateway.dao.rule_dao import RuleDAO

e = EnvInit()

## request max size 500MB
ENV_SANIC_REQUEST_MAX_SIZE = 500000000
## request timeout 1h
ENV_SANIC_REQUEST_TIMEOUT = 3600
## response timeout 1h
ENV_SANIC_RESPONSE_TIMEOUT = 3600

ASYNC_SESSION_TIMEOUT = e.ASYNC_SESSION_TIMEOUT or 5 * 60
ASYNC_REQUEST_TIMEOUT = e.get("ASYNC_REQUEST_TIMEOUT", 60 * 15)  # NO RESTART
SESSION_TIMEOUT = e.get("SESSION_TIMEOUT", 60 * 60)

PORT = e.get("PORT", 8080)
AUTOSCAN = e.get("AUTOSCAN", True)
RULES = e.RULES or []  # ,["file-converter", "localhost", 7070],["ds4biz-textract", "localhost", 8081],["predictor", "localhost", 8081],["nlp", "localhost", 9090],["cloudstorage", "localhost", 8083]]
print(e.RULES, type(e.RULES))
AUTO_RELOAD = e.AUTO_RELOAD or False
SERVICE_DEBUG = e.SERVICE_DEBUG or False

RULES_DAO = RuleDAO()
