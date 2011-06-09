import os
import json
import types
import collections

import archon.objects
import archon.datahandlers


# TODO possibly use super() as described
# http://rhettinger.wordpress.com/2011/05/26/super-considered-super/ to
# implement mixin classes for datastore storage and type (e.g. a file-based
# storage mechanism and a JSON type, or a DB and binary) Probably not
# needed, though
class Datastore(object):

    def __init__(self, parent=None):
        pass

    def add(self, key, item):
        pass

    def remove(self, key):
        pass

    def __getitem__(self, key):
        pass

    @property
    def root(self):
        pass






class GameDatastore(Datastore):
    """
    A JSON and file-based datastore.
    """

    def __init__(self, path, parent=None):
        self._path = os.path.abspath(path)
        self._name = os.path.basename(os.path.normpath(path))
        # normpath deals with trailing slash, basename gets directory name
        self.parent = parent
        self._cache = {}
        self._didLoad = collections.defaultdict(lambda: False)
        # don't add myself - my parent takes care of it
        for fname in os.listdir(self._path):
            fullpath = os.path.join(self._path, fname)
            if os.path.isfile(fullpath):
                entityID, ext = os.path.splitext(fname)
                if archon.datahandlers.dataparser.contains(ext):
                    loader = archon.datahandlers.dataparser.get(ext)
                    data = loader(open(fullpath).read())
                    if data and archon.datahandlers.dataloader.contains(
                        data['type']
                        ):
                        self.add(
                            entityID,
                            lambda key=entityID, data=data:
                                self.load(key, data))
            elif os.path.isdir(fullpath):
                child = self.__class__(fullpath, self)
                self.add(child.name,
                         lambda child=child: child)

    def load(self, key, data):
        """
        Load the given data. This is an internal method!
        """
        objtype = data['type']
        objdata = data['data']
        if archon.datahandlers.dataloader.contains(objtype):
            obj = archon.datahandlers.dataloader.get(objtype)(
                key,
                objdata,
                self
                )
            return obj

    def add(self, key, item):
        if not type(item) in (types.FunctionType, types.MethodType):
            self._didLoad[key] = True  # Strict add
        self._cache[key] = item

    def remove(self, key):
        del self._cache[key]

    @property
    def name(self):
        return self._name

    @property
    def root(self):
        if self.parent:
            return self.parent.root
        else:
            return self

    def __getitem__(self, key):
        if '.' in key:
            key, subkey = key.split('.', 1)
            return self[key][subkey]
        else:
            if not self._didLoad[key]:
                self._cache[key] = self._cache[key]()
                self._didLoad[key] = True
            return self._cache[key]

    def __contains__(self, key):
        if '.' in key:
            key, subkey = key.split('.', 1)
            return key in self._cache and subkey in self[key]
        else:
            return key in self._cache
