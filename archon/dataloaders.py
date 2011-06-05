import archon.common
import archon.objects

ENTITY_TYPE = 'entity'
ROOM_TYPE = 'room'
DATA_TYPE = 'data'
TYPES_SUPPORTED = (ENTITY_TYPE, ROOM_TYPE, DATA_TYPE)
# Types dictate loading, kind denotes semantic data ("room" vs "indoors")


class dataloader(archon.common.denoter):
    pass


@dataloader(ENTITY_TYPE)
def entity(key, data, cache, superCache):
    kind = data['kind']
    entity = archon.objects.Entity(key, kind)
    cache.add(key, entity)
    for name, data in data['attributes'].iteritems():
        entity.attributes[name] = data
    return entity

DATA_PREFIXES = {
    '!': 'description',
    '@': 'location',
    '<': 'prefix',
    '?': 'identity',
    '*': 'options'
    }


@dataloader(ROOM_TYPE)
def room(key, data, cache, superCache):
    kind, description = data['kind'], data['describe']
    room = archon.objects.Room(key, kind, description, cache)

    for name, val in data['attributes'].iteritems():
        room.attributes[name] = val

    contents = []
    for eKey, eData in data['contents'].iteritems():
        entityInfo = {'identity': eKey}
        entityKind = None
        for item in eData:
            if item[0] not in DATA_PREFIXES:
                entityKind = item
            else:
                entityInfo[DATA_PREFIXES[item[0]]] = item[1:]
        if 'options' in entityInfo:
            entityInfo['options'] = entityInfo['options'].split(',')
        contents.append((entityKind, eKey, entityInfo))
    ids = [eInfo.get('identity', eKey) for _, eKey, eInfo in contents]
    for eKind, eKey, eInfo in contents:
        # identity (or key) is not unique, no prefix and the key collides
        # with an identity
        identity = eInfo.get('identity', eKey)
        if 'prefix' not in eInfo and ids.count(identity) > 1:
            # we need to generate a prefix
            # this algorithm is awkward because if there is no 'a thing',
            # but 'thing' and 'another thing' are present, it generates 'yet
            # another thing' automatically
            eInfo['prefix'] = ('yet another ' *
                               (ids.count(identity) - 1)).strip()

    for eKind, eKey, eInfo in contents:
        room.add(eKind, eKey, **eInfo)

    cache.add(key, room)

    for direction, target in data['outputs'].iteritems():
        # cache, then supercache (relative, then absolute)
        if target in cache:
            troom = cache[target]
        elif target in superCache:
            troom = superCache[target]
        else:
            raise ValueError("Room {} not found!".format(target))
        room.add(
            archon.objects.Room.ROOM_ENTITY_KIND,
            direction,
            troom)
    return room
