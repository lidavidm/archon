import os
import json

import archon.objects
import archon.actions


class Datastore(object):
    def __init__(self, path):
        pass

    def __getitem__(self, key):
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


class JSONDatastore(Datastore):
    ENTITY_TYPE = 'entity'
    ROOM_TYPE = 'room'

    ENTITY_DATA_PREFIXES = {
        '!': 'description',
        '@': 'location',
        '<': 'prefix',
        '?': 'identity'
        }

    def __init__(self, path):
        self._path = path

    def load(self, key):
        try:
            data = json.load(open(os.path.join(self._path, key)))
        except ValueError:
            raise ValueError("Invalid JSON document")

        objtype = data['type']
        objdata = data['data']
        if objtype == self.__class__.ENTITY_TYPE:
            ekind = objdata['entity_kind']
            entity = archon.objects.Entity(ekind)
            del objdata['entity_kind']
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
            # We need to hold on to the room. When it is exited/deleted,
            # serialize the changes to disk.
            # We also need a database that allows the room to look up
            # entities as needed. However, we won't handle this; the game
            # code will manage this responsibility.
            roomKind = objdata['kind']
            room = archon.objects.Room(roomKind, objdata['describe'])

            contents = []
            for eKey, eData in objdata['contents'].iteritems():
                entityInfo = {'identity': eKey}
                entityKind = None
                for item in eData:
                    if item[0] not in self.__class__.ENTITY_DATA_PREFIXES:
                        entityKind = item
                    else:
                        entityInfo[
                            self.__class__.ENTITY_DATA_PREFIXES[item[0]]
                            ] = item[1:]
                contents.append((entityKind, eKey, entityInfo))

            ids = [eInfo.get('identity', eKey)
                   for _, eKey, eInfo in contents]
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
                room.add(eKind, eKey, **eInfo)

            return room

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
