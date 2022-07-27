import json

from loko_gateway.utils.resources_utils import get_resource


class HostsDAO:
    def __init__(self, hosts_path = None):
        self.hosts_path = hosts_path
        self._hosts_dict = None

    def _save(self):
        print('SAVE!!')
        with open(self.hosts_path, 'w') as f:
            json.dump(list(self.hosts_dict.values()), f)

    @property
    def hosts_dict(self):
        if self._hosts_dict is None:
            if self.hosts_path:
                with open(self.hosts_path, 'r') as f:
                    hosts = json.load(f)
                    self._hosts_dict = {f'{host}:{port}': [mount, host, port] for mount, host, port in hosts}
            else:
                self._hosts_dict = {}
        return self._hosts_dict

    def all(self):
        return self.hosts_dict

    def save(self, hosts):
        new_hosts = {f'{host}:{port}': [mount, host, port] for mount, host, port in hosts}
        self.hosts_dict.update(new_hosts)
        if self.hosts_path:
            self._save()

    def delete(self, host):
        k = [k for k, v in self.hosts_dict.items() if host in v]
        if not k:
            raise Exception('host not present')
        del self.hosts_dict[k[0]]
        if self.hosts_path:
            self._save()

hosts_path = get_resource("hosts/hosts.json")
with open(hosts_path, 'w') as f:
    json.dump([], f)
hostsdao = HostsDAO(hosts_path)

