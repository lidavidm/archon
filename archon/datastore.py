import os
import json

import archon.objects


class Datastore(object):
    def __init__(self, path):
        pass

    def __getitem__(self, key):
        pass


class JSONDatastore(Datastore):
    def __init__(self, path):
        self._path = path

    def load(self, key):
        try:
            data = json.load(os.path.join(self._path, key))
        except ValueError:
            raise ValueError("Invalid JSON document")

    def __getitem__(self, key):
        if key in self:
            path = os.path.join(self._path, key)
            if os.path.isdir(path):
                return self.__class__(path)
            else:
                return self.load(key)
        else:
            raise KeyError(key)

    def __contains__(self, key):
        return os.path.exists(os.path.join(self._path, key))
