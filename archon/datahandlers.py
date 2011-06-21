import json
import warnings

import archon.common
import archon.objects

ENTITY_TYPE = 'entity'
ROOM_TYPE = 'room'
DATA_TYPE = 'data'
SCRIPT_TYPE = 'script'
AREA_TYPE = 'area'
JSON_DIFF_TYPE = 'jsondiff'  # TODO: structural diff of JSON for saves
# Types dictate loading, kind denotes semantic data ("room" vs "indoors")


class dataloader(archon.common.denoter):
    """Denotes a function that takes JSON and creates an object."""


class dataparser(archon.common.denoter):
    """Denotes a function that converts a file to a JSON-like representation
    of the data."""


class dataserializer(archon.common.denoter):
    """Denotes a function that takes an object and creates JSON.

    Private properties should not be needed by this function; ideally, the
    public API of the object should expose all the needed information to
    save it to disk.
    """


@dataparser('.json')
def jsonType(contents):
    try:
        data = json.loads(contents)
        assert 'type' in data
        assert 'data' in data
        return data
    except ValueError:
        warnings.warn("Error loading JSON data!",
                      RuntimeWarning, stacklevel=2)
        return None
    except AssertionError:
        warnings.warn('JSON data is not well-formed!',
                      RuntineWarning, stacklevel=2)
        return None


@dataparser('.py')
def pythonType(contents):
    return {"type": SCRIPT_TYPE, "data": contents}


@dataloader(ENTITY_TYPE)
def entity(key, data, cache):
    kind = data['kind']
    entity = archon.objects.Entity(key, kind, data['attributes'])
    return entity


@dataloader(AREA_TYPE)
def area(key, data, cache):
    name = data['name']
    area = archon.objects.Entity(key, 'area')
    area.entityCache = cache
    area.attributes['name'] = name
    area.attributes.update(data['attributes'])
    return area


@dataloader(ROOM_TYPE)
def room(key, data, cache):
    description = data['describe']
    room = archon.objects.Room(key, description, cache)

    for name, val in data['attributes'].items():
        room.attributes[name] = val

    contents = []
    for eKey, eData in data['contents'].items():
        entityInfo = {}
        entityLocation = eData['entity']

        if ',' in eKey:
            eKey, prefix = eKey.split(',')
            prefix = prefix.strip()
            eKey = archon.objects.EntityKey(eKey, prefix)
            entityInfo['prefix'] = prefix

        if 'options' in eData:
            eData['options'] = eData['options'].split(',')
        entityInfo.update(eData)
        del entityInfo['entity']  # this key doesn't need to be there
        contents.append((entityLocation, eKey, entityInfo))
    ids = [eKey for _, eKey, _ in contents]
    for eLocation, eKey, eInfo in contents:
        # identity (or key) is not unique, no prefix and the key collides
        # with an identity
        if 'prefix' not in eInfo and ids.count(eKey) > 1:
            # we need to generate a prefix
            eInfo['prefix'] = ('yet another ' *
                               (ids.count(Key) - 1)).strip()

    for eLocation, eKey, eInfo in contents:
        room.add(eLocation, eKey, **eInfo)

    # Load the area if present.
    if 'area' in cache:
        room.area = cache['area']

    # Unlike the others, this MUST be here to break circular references when
    # loading rooms (although the thunk is present in the cache,
    # dereferencing it will cause a loop where we continually reload the
    # same room)
    cache.add(key, room)

    for direction, target in data['outputs'].items():
        try:
            troom = cache.lookup(target)
            room.addRoom(direction, troom)
        except KeyError:
            raise ValueError("Room {} not found!".format(target))
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
    return compile(data, '<string>', 'exec')
