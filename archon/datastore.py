"""
Defines the game database, a mapping from JSON to game objects.
"""

import os
import json
import types
import collections

import archon.objects
import archon.datahandlers


class DataThunk:
    """
    Represents an unloaded object.
    """
    def __init__(self, ds, key, data):
        self.ds = ds
        self.key = key
        self.data = data

    def __call__(self):
        # for code that checks with callable()
        item = self.ds.load(self.key, self.data)
        self.ds._didLoad[self.key] = True
        self.ds._cache[self.key] = item
        return item

    evaluate = __call__


# TODO possibly use super() as described
# http://rhettinger.wordpress.com/2011/05/26/super-considered-super/ to
# implement mixin classes for datastore storage and type (e.g. a file-based
# storage mechanism and a JSON type, or a DB and binary) Probably not
# needed, though
class Datastore:
    """
    The basic Datastore class.
    """

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
    A lazy, mostly-read datastore.

    This datastore, when created, will scan its directory for possible game
    files (any that have a file extension specified by
    archon.datahandlers.dataparser), but will not load them until an object
    requests them. After loaded, the datastore will continue to hold on to
    the object. No changes made will be saved unless the save() method is
    called.
    """

    def __init__(self, path, parent=None):
        self._path = os.path.abspath(path)
        self._name = os.path.basename(os.path.normpath(path))
        # normpath deals with trailing slash, basename gets directory name
        self.parent = parent
        self._cache = {}
        self._didLoad = collections.defaultdict(lambda: False)
        self._shouldSave = set()
        # don't add myself - my parent takes care of it
        for fname in os.listdir(self._path):
            fullpath = os.path.join(self._path, fname)
            if os.path.isfile(fullpath):
                key, data = self.raw(fname)
                if data and archon.datahandlers.dataloader.contains(
                    data['type']
                    ):
                    self.add(key, DataThunk(self, key, data))
            elif os.path.isdir(fullpath):
                child = self.__class__(fullpath, self)
                self.add(child.name, child)

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

    def save(self, key, data=None, immediately=False):
        """
        Save the data to disk, or if the key exists, mark it for saving.

        By default, GameDatastore will not save any changes to disk. If
        changes should be saved, then call this method to mark it for
        saving. The data will not be immediately saved unless otherwise
        specified; instead, it will be saved at the end of the datastore's
        lifetime. This method can also add a new object to the database at
        runtime.
        """
        self._shouldSave.add(key)
        if data:
            self.add(key, data)
        if immediately:
            json.dump(data,
                      open(os.path.join(self._path, key + '.json'), 'w'),
                      indent=1,
                      cls=EntityJSONEncoder)

    def add(self, key, item):
        """Add an item into the datastore."""
        self._cache[key] = item
        if not isinstance(item, DataThunk):
            self._didLoad[key] = True  # Strict add

    def remove(self, key):
        """Remove an item from the datastore."""
        del self._cache[key]

    def keys(self):
        return self._cache.keys()

    def create(self, key):
        """Create a sub-datastore with the given name."""
        assert key not in self
        fullpath = os.path.join(self._path, key)
        os.mkdir(fullpath)
        child = self.__class__(fullpath, self)
        self.add(child.name, child)
        return child

    def raw(self, key, format=None):
        """Returns the raw dict object loaded by the datastore.

        If `key` is a filename, pass in a format of `None`. Else, `format`
        should be a file extension (with period)."""
        if not format:
            key, format = os.path.splitext(key)
        fullpath = os.path.join(self._path, key + format)
        if os.path.isfile(fullpath):
            if archon.datahandlers.dataparser.contains(format):
                loader = archon.datahandlers.dataparser.get(format)
                data = loader(open(fullpath).read())
                if not data:
                    raise ValueError('Error loading data from ' + fullpath)
                return key, data
            else:
                raise ValueError(
                    'Format {} unsupported (key {} in {})'.format(
                        format, key, self.name))
        else:
            raise IOError('No such key {} (format {}) in {}'.format(
                    key, format, self.name))

    @property
    def name(self):
        """The name of this datastore (the folder name)."""
        return self._name

    @property
    def fullName(self):
        """The full name: the name of the parent with my name."""
        names = [self.name]
        current = self
        while current.parent:
            names.append(current.parent.name)
            current = current.parent
        return '.'.join(reversed(names))

    @property
    def root(self):
        """The root, which contains all other datastores."""
        if self.parent:
            return self.parent.root
        else:
            return self

    @property
    def isRoot(self):
        return not self.parent

    @property
    def thunks(self):
        return self._cache

    def lookup(self, key):
        """Convenience function: try relative, then absolute."""
        if key in self:
            return self[key]
        else:
            return self.root[key]

    def __iter__(self):
        for key in self._cache:
            yield key

    def datastoreFor(self, key):
        """Find the containing datastore of the given key."""
        if self.isRoot and key.split('.', 1)[0] == self.name:
            return self.datastoreFor(key.split('.', 1)[1])
        elif key.startswith('.'):  # absolute lookup
            return self.root.datastoreFor(key[1:])
        elif '.' in key:
            key, subkey = key.split('.', 1)
            # get the parent datastore, then the datastore itself
            return self.datastoreFor(key)[1][key].datastoreFor(subkey)
        else:
            return key, self

    def thunkFor(self, key):
        """Get the thunk if possible, else the object/datastore."""
        key, ds = self.datastoreFor(key)
        if key not in ds._cache:
            raise KeyError(key)
        return ds._cache[key]

    def __getitem__(self, key):
        thunk = self.thunkFor(key)
        if isinstance(thunk, DataThunk):
            thunk = thunk.evaluate()
        return thunk

    def __contains__(self, key):
        if '.' in key:
            key, subkey = key.split('.', 1)
            return key in self._cache and subkey in self[key]
        else:
            return key in self._cache

    def __bool__(self):
        return bool(self._cache)


class EntityJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, archon.objects.Entity):
            # TODO check for mutable entities
            return o.location
        else:
            return super().default(o)
