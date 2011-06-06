import collections


class EntityHookNotFoundError(Exception):pass


class EntityHook(collections.MutableMapping):
    """
    Defines special behavior for the attributes of certain entity kinds.
    """
    KIND = ''

    def __init__(self, entity):
        self._attributes = {}

    def __len__(self):
        return len(self._attributes)

    def __iter__(self):
        return self._attributes.__iter__()

    def __contains__(self, key):
        return key in self._attributes

    def __getitem__(self, key):
        """Override for custom behavior. """
        return self._attributes.__getitem__(key)

    def __setitem__(self, key, value):
        """Override for custom behavior."""
        return self._attributes.__setitem__(key, value)

    def __delitem__(self, key):
        """Override for custom behavior."""
        return self._attributes.__delitem__(key)

    @property
    def attributes(self):
        return self._attributes

    @classmethod
    def get(cls, kind):
        if cls.KIND == kind:
            return cls
        else:
            for subcls in cls.__subclasses__():
                try:
                    return subcls.get(kind)
                except EntityHookNotFoundError:
                    continue
        raise EntityHookNotFoundError(kind)


class RoomEntityHook(EntityHook):
    KIND = "room"
    def __init__(self, entity):
        super(RoomEntityHook, self).__init__(entity)
        self.attributes.update(
            friendlyName=entity.name
            )


class Entity(object):
    def __init__(self, name, kind):
        self.name = name
        self.kind = kind
        try:
            kindhook = EntityHook.get(kind)
            self._attributes = kindhook(self)
        except EntityHookNotFoundError:
            self._attributes = {}

    @property
    def attributes(self):
        return self._attributes

    @attributes.setter
    def attributes(self, value):
        self._attributes.update(value)


EntityData = collections.namedtuple(
    'EntityData',
    'kind identity location description prefix options'
    )


class Room(Entity):
    ROOM_ENTITY_KIND = 'room'

    def __init__(self, name, kind, description, cache):
        super(Room, self).__init__(name, Room.ROOM_ENTITY_KIND)
        self.attributes[kind] = kind
        # Problem: kind here is "indoors", "outdoors", etc.
        # but the Entity kind is really "room", "npc"...
        self._description = description
        self._entityCache = cache
        self._contents = {}
        self._outputs = {}

    def naturalFind(self, text):
        """
        Attempt to find an entity key based on a variety of criteria.

        Returns None if there is no match.

        If there is no unique entity matched, return a set of all possible
        matches. Else, return the only match.
        """
        # identity, prefix-identity, or key, with key taking precedence
        matches = set()
        if text in self.contents:  # it's a key
            matches.add(text)

        crit = text.split()
        if not crit:
            return None

        # find all entities for the identity specified
        for key, entity in self.contents.iteritems():
            if entity[1] == crit[-1]:
                matches.add(key)
        if matches:
            if len(matches) == 1:
                return matches.pop()  # only one match
            if len(crit) > 1:  # there's a prefix
                prefix = text[:-len(crit[-1])].rstrip()  # get the prefix
                for key, entity in self.contents.iteritems():
                    if entity[4] == prefix and entity[1] == crit[-1]:
                        return key  # prefix-identity should be unique
            return matches
        return None

    def add(self, entityKind, key, identity,
            location='', description='', prefix='', options=None):
        """
        Add an entity or output to the room.

        :param entityKind: The entity's kind. If adding a room, set this to
                           self.ROOM_ENTITY_KIND.
        :param key: The key for the entity. If adding a room, this is the
                    direction.
        :param identity: The identity for the entity. If adding a room, this
                         is the target room.
        :param location: The location description for the entity.
        :param description: A description of the entity.
        :param options: Options for the entity.
        """
        if entityKind is self.ROOM_ENTITY_KIND:
            # key is direction, identity is
            # the target
            self._outputs[key] = identity
        else:
            if options is None:
                options = []
            self._contents[key] = EntityData(entityKind, identity,
                                   location, description, prefix, options)

    def remove(self, key):
        del self._contents[key]

    def describe(self, key=None):
        """
        Describe the specified object, or if not given, the room.
        """
        if key:
            entity = self.allContents[key]
            beginning = ''
            if key in self.contents:
                text = 'There is {prefix}{identity}{location}.'.format(
                beginning=beginning,
                prefix=entity[4] + ' ' if entity[4] else '',
                identity=entity[1],
                location=' ' + entity[2] if entity[2] else ''
                ).strip()
                if entity[3]:
                    text = ' '.join([text, 'It is', entity[3] + '.'])
                return text
            elif key in self.outputs:
                return 'You can go {}.'.format(key)
        else:
            return '\n'.join(
                ['You are in ' + self._description] +
                [self.describe(key) for key in sorted(self.contents)] +
                [self.describe(key) for key in self.outputs])

    def enter(self):
        pass

    def exit(self):
        pass

    @property
    def entityCache(self):
        return self._entityCache

    @entityCache.setter
    def entityCache(self, cache):
        self._entityCache = cache

    @property
    def contents(self):
        return self._contents

    @property
    def outputs(self):
        return self._outputs

    @property
    def allContents(self):
        return UnionDict(self.contents, self.outputs)

    @property
    def inputs(self):
        pass


class UnionDict(dict):
    def __init__(self, *dicts):
        self._dicts = dicts

    def __getitem__(self, key):
        for dictionary in self._dicts:
            if key in dictionary:
                return dictionary[key]
        raise KeyError(key)


class Player(object):
    pass
