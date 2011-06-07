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

class CacheDatastore(Datastore):
    """
    Holds objects.
    """
    def __init__(self, parent=None):
        self._cache = {}
        self.parent = parent

    def add(self, key, item):
        self._cache[key] = item

    def remove(self, key):
        del self._cache[key]

    def __getitem__(self, key):
        if '.' in key:
            key, subkey = key.split('.', 1)
            return self._cache[key][subkey]
        return self._cache[key]

    def __contains__(self, key):
        return key in self._cache

    @property
    def root(self):
        if self.parent:
            return self.parent.root
        else:
            return self


class LazyCacheDatastore(CacheDatastore):
    def __init__(self, parent=None):
        super(LazyCacheDatastore, self).__init__(parent)
        self._didLoad = collections.defaultdict(lambda: False)

    def add(self, key, item):
        if not type(item) in (types.FunctionType, types.MethodType):
            # Strict add
            self._didLoad[key] = True
        super(LazyCacheDatastore, self).add(key, item)

    def __getitem__(self, key):
        subkey = None
        if '.' in key:
            key, subkey = key.split('.', 1)
        if key not in self._cache:
            raise KeyError(key)
        if not self._didLoad[key]:
            self._cache[key] = self._cache[key]()
            self._didLoad[key] = True
        if subkey:
            return super(LazyCacheDatastore, self).__getitem__(subkey)
        else:
            return super(LazyCacheDatastore, self).__getitem__(key)


class GameDatastore(Datastore):
    """
    A JSON and file-based datastore.
    """

    def __init__(self, path, cacheType, parent=None):
        self._path = os.path.abspath(path)
        self._name = os.path.basename(os.path.normpath(path))
        # normpath deals with trailing slash, basename gets directory name
        self.parent = parent
        parentCache = None if parent is None else parent._cache
        self._cache = cacheType(parentCache)
        # don't add myself - my parent takes care of it
        for fname in os.listdir(self._path):
            fullpath = os.path.join(self._path, fname)
            if os.path.isfile(fullpath):
                entityID, ext = os.path.splitext(fname)
                if archon.datahandlers.dataparser.contains(ext):
                    loader = archon.datahandlers.dataparser.get(ext)
                    data = loader(open(fullpath).read())
                    if data is None:
                        continue
                    elif archon.datahandlers.dataloader.contains(
                        data['type']
                    ):
                        self._cache.add(
                            entityID,
                            lambda key=entityID, data=data:
                                self.load(key, data)
                            )
            elif os.path.isdir(fullpath):
                child = self.__class__(fullpath, cacheType, self)
                self._cache.add(child.name, lambda: child)

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
                self._cache
                )
            return obj

    @property
    def name(self):
        return self._name

    def __getitem__(self, key, subkey=None):
        if '.' in key:
            key, subkey = key.split('.', 1)
            return self.__getitem__(key, subkey)
        target = None
        if key in self._cache:
            target = self._cache[key]
        else:
            raise KeyError(key)
        if subkey:
            return target[subkey]
        else:
            return target

    def __contains__(self, key):
        if '.' in key:
            key, subkey = key.split('.', 1)
            return key in self._cache and subkey in self._cache[key]
        else:
            return key in self._cache
