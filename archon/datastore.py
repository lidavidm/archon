import os
import json
import types
import collections

import archon.objects
import archon.actions
import archon.dataloaders


# TODO possibly use super() as described
# http://rhettinger.wordpress.com/2011/05/26/super-considered-super/ to
# implement mixin classes for datastore storage and type (e.g. a file-based
# storage mechanism and a JSON type, or a DB and binary) Probably not
# needed, though
class Datastore(object):

    def __init__(self, path):
        pass

    def add(self, key, item):
        pass

    def remove(self, key):
        pass

    def __getitem__(self, key):
        pass

    @property
    def rooms(self):
        pass

    @property
    def entities(self):
        pass


class CacheDatastore(Datastore):
    """
    Holds objects.
    """
    def __init__(self):
        self._cache = {}

    def add(self, key, item):
        self._cache[key] = item

    def remove(self, key):
        del self._cache[key]

    def __getitem__(self, key):
        return self._cache[key]

    def __contains__(self, key):
        return key in self._cache


class LazyCacheDatastore(CacheDatastore):
    def __init__(self):
        super(LazyCacheDatastore, self).__init__()
        self._didLoad = collections.defaultdict(lambda: False)

    def add(self, key, item):
        if not type(item) in (types.FunctionType, types.MethodType):
            # Strict add
            self._didLoad[key] = True
        super(LazyCacheDatastore, self).add(key, item)

    def __getitem__(self, key):
        if key not in self._cache:
            raise KeyError(key)
        if not self._didLoad[key]:
            self._cache[key] = self._cache[key]()
            self._didLoad[key] = True
        return super(LazyCacheDatastore, self).__getitem__(key)


class GameDatastore(Datastore):
    """
    A JSON and file-based datastore.
    """

    def __init__(self, path, cache):
        self._path = os.path.abspath(path)
        self._name = os.path.basename(os.path.normpath(path))
        # normpath deals with trailing slash, basename gets directory name
        if type(cache) == types.ClassType:  # top level
            self._cache = self._superCache = cache()
        else:
            self._superCache = cache
            self._cache = cache.__class__()
            # don't add myself - my parent takes care of it
        for fname in os.listdir(self._path):
            fullpath = os.path.join(self._path, fname)
            if os.path.isfile(fullpath):
                entityID, ext = os.path.splitext(fname)
                if ext.lower() == '.json':
                    try:
                        data = json.load(open(fullpath))
                    except ValueError:
                        continue
                    if ('type' in data and
                        data['type'] in archon.dataloaders.TYPES_SUPPORTED):
                        self._cache.add(
                            entityID,
                            lambda key=entityID: self.load(key, again=True)
                            )
            elif os.path.isdir(fullpath):
                child = self.__class__(key, cache)
                self._cache.add(child.name, lambda: child)

    def load(self, key, again=False):
        """
        Load the given key. Do not specify a file extension.

        :param again: If True, reload from scratch, ignoring the cache.
        """
        if not again and key in self._cache:
            return self._cache[key]
        try:
            data = json.load(open(os.path.join(self._path, key + '.json')))
        except ValueError:
            raise ValueError("Invalid JSON document")

        key = key.lower()  # XXX case insensitive -- needs doc+rationale
        # problem: on linux it will be case sensitive...

        objtype = data['type']
        objdata = data['data']

        if objtype in archon.dataloaders.TYPES_SUPPORTED:
            obj = archon.dataloaders.dataloader.get(objtype)(
                key,
                objdata,
                self._cache,
                self._superCache
                )
            return obj

    @property
    def name(self):
        return self._name

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
        return os.path.exists(os.path.join(self._path, key + '.json'))
