import logging


def error_handler(f):
    def ff(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logging.exception(e)
    return ff