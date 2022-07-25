from collections import defaultdict


class Observable:
    def __init__(self):
        self.observers = defaultdict(list)
    def add_observer(self, event, obs):
        # gli observer sono funzioni che vengono lanciate quando si verifica un evento
        self.observers[event].append(obs)
    async def notify(self, event, data):
        for obs in self.observers[event]:
            await obs(data)

class UploadLimit:
    def __init__(self, limit):
        self.limit = limit
    def set_limit(self, limit):
        print("Refreshing/updating limit")
        self.limit = limit