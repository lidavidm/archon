import json

import archon.common
import archon.objects

ENTITY_TYPE = 'entity'
ROOM_TYPE = 'room'
DATA_TYPE = 'data'
SCRIPT_TYPE = 'script'
JSON_DIFF_TYPE = 'jsondiff'  # TODO: structural diff of JSON for saves
# Types dictate loading, kind denotes semantic data ("room" vs "indoors")


class dataloader(archon.common.denoter):
    """Denotes a function that takes JSON and creates an object."""


class dataparser(archon.common.denoter):
    """Denotes a function that takes a file and returns JSON."""


@dataparser('.json')
def jsonType(contents):
    try:
        data = json.loads(contents)
        assert 'type' in data
        assert 'data' in data
        return data
    except (ValueError, AssertionError):
        return None


@dataparser('.py')
def pythonType(contents):
    return {"type": SCRIPT_TYPE, "data": contents}


@dataloader(ENTITY_TYPE)
def entity(key, data, cache):
    kind = data['kind']
    entity = archon.objects.Entity(key, kind)
    for name, data in data['attributes'].items():
        entity.attributes[name] = data
    return entity


@dataloader(ROOM_TYPE)
def room(key, data, cache):
    kind, description = data['kind'], data['describe']
    room = archon.objects.Room(key, kind, description, cache)

    for name, val in data['attributes'].items():
        room.attributes[name] = val

    contents = []
    for eKey, eData in data['contents'].items():
        entityInfo = {'identity': eKey}
        entityKind = eData['entity']
        if 'options' in eData:
            eData['options'] = eData['options'].split(',')
        entityInfo.update(eData)
        del entityInfo['entity']  # this key doesn't need to be there
        contents.append((entityKind, eKey, entityInfo))
    ids = [eInfo.get('identity', eKey) for _, eKey, eInfo in contents]
    for eKind, eKey, eInfo in contents:
        # identity (or key) is not unique, no prefix and the key collides
        # with an identity
        identity = eInfo.get('identity', eKey)
        if 'prefix' not in eInfo and ids.count(identity) > 1:
            # we need to generate a prefix
            eInfo['prefix'] = ('yet another ' *
                               (ids.count(identity) - 1)).strip()

    for eKind, eKey, eInfo in contents:
        room.add(eKind, eKey, **eInfo)

    # Unlike the others, this MUST be here to break circular references when
    # loading rooms (although the thunk is present in the cache,
    # dereferencing it will cause a loop where we continually reload the
    # same room)
    cache.add(key, room)

    for direction, target in data['outputs'].items():
        if target in cache:
            troom = cache[target]
        elif cache.root and target in cache.root:  # absolute lookup
            troom = cache.root[target]
        else:
            raise ValueError("Room {} not found!".format(target))
        room.add(
            archon.objects.Room.ROOM_ENTITY_KIND,
            direction,
            troom)
    return room


@dataloader(DATA_TYPE)
def data(key, data, cache):
    """
    Loads unstructured JSON data, essentially.
    """
    # Possibly look for "#reference(key)" strings and replace them so that
    # links to other data files can be made?
    return data


@dataloader(SCRIPT_TYPE)
def script(key, data, cache):
    """Loads a Python script."""
    return data
