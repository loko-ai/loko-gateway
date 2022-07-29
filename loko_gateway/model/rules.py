class Rule:
    """"""

    def __init__(self, name, host, port, type=None, base_path=None, **metadata):
        """Constructor for Rule"""
        self.name = name
        self.host = host.strip("/")
        self.port = port
        self.type = type
        self.base_path = base_path or ""
        self.metadata = metadata or {}
