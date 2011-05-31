import os
import json
import types
import collections

import archon.objects
import archon.actions


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
        self._didLoad = collections.defaultdict(lambda:False)

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


def parseContents(contentData, dataPrefixes):
    """
    Parses a room's contents.
    """
    contents = []
    for eKey, eData in contentData.iteritems():
        entityInfo = {'identity': eKey}
        entityKind = None
        for item in eData:
            if item[0] not in dataPrefixes:
                entityKind = item
            else:
                entityInfo[dataPrefixes[item[0]]] = item[1:]
        if 'options' in entityInfo:
            entityInfo['options'] = entityInfo['options'].split(',')
        contents.append((entityKind, eKey, entityInfo))
    ids = [eInfo.get('identity', eKey) for _, eKey, eInfo in contents]
    for eKind, eKey, eInfo in contents:
        # identity (or key) is not unique,
        # no prefix and the key collides with an identity
        identity = eInfo.get('identity', eKey)
        if 'prefix' not in eInfo and ids.count(identity) > 1:
            # we need to generate a prefix
            # this algorithm is awkward because if there is no 'a
            # thing', but 'thing' and 'another thing' are present,
            # it generates 'yet another thing' automatically
            eInfo['prefix'] = ('yet another ' *
                               (ids.count(identity) - 1)).strip()
    return contents


class JSONDatastore(Datastore):
    """
    A JSON and file-based datastore.
    """
    ENTITY_TYPE = 'entity'
    ROOM_TYPE = 'room'

    DATA_PREFIXES = {
        '!': 'description',
        '@': 'location',
        '<': 'prefix',
        '?': 'identity',
        '*': 'options'
        }

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
                        data['type'] in (self.__class__.ENTITY_TYPE,
                                         self.__class__.ROOM_TYPE)):
                        self._cache.add(
                            entityID,
                            lambda key=entityID: self.load(key, again=True)
                            )
            elif os.path.isdir(fullpath):
                child = self.__class__(key, cache)
                self._cache.add(child.name, lambda:child)

    def load(self, key, again=False):
        """
        Load the given key. Do not specify a file extension.

        :param again: If True, reload from scratch, ignoring the cache.
        """
        # search the cache unless otherwise specified
        if not again and key in self._cache:
            return self._cache[key]
        try:
            data = json.load(open(os.path.join(self._path, key+'.json')))
        except ValueError:
            raise ValueError("Invalid JSON document")

        objtype = data['type']
        objdata = data['data']
        if objtype == self.__class__.ENTITY_TYPE:
            ekind = objdata['entity_kind']
            eattr = objdata['entity_attributes']
            entity = archon.objects.Entity(ekind)
            entity.attributes = eattr
            del objdata['entity_kind']
            del objdata['entity_attributes']
            for name, actions in objdata.iteritems():
                actionFuncs = []
                if isinstance(actions, basestring):
                    # ``actions`` is a string, treat it as a notification
                    action = archon.actions.getAction('ui.notify')
                    actionFuncs.append((action, [actions]))
                else:
                    for actionData in actions:
                        actionName = actionData[0]
                        actionParams = actionData[1:]
                        action = archon.actions.getAction(actionName)
                        actionFuncs.append((action, actionParams))

                entity.when(name, actionFuncs)

            return entity

        elif objtype == self.__class__.ROOM_TYPE:
            roomKind = objdata['kind']
            room = archon.objects.Room(roomKind, objdata['describe'])
            for eKind, eKey, eInfo in parseContents(
                objdata['contents'],
                self.__class__.DATA_PREFIXES
                ):
                room.add(eKind, eKey, **eInfo)

            # To avoid circular references, add the current room to the
            # cache, list all the needed rooms, then load each one, looking
            # them up in the cache first
            self._cache.add(key, room)
            for direction, target in objdata['outputs'].iteritems():
                # Look in this cache, then the super cache
                # i.e. try relative, then absolute
                if target in self._cache:
                    troom = self._cache[target]
                elif target in self._superCache:
                    troom = self._superCache[target]
                else:
                    raise ValueError(
                        'Room {} referenced does not exist'.format(target)
                        )
                room.add(room.ROOM_ENTITY_KIND, direction, troom)

            return room

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
        return os.path.exists(os.path.join(self._path, key+'.json'))
