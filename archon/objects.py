import math
import types
import random
import datetime
import collections


class EntityHookNotFoundError(Exception): pass


class EntityHook(collections.MutableMapping):
    """
    Defines special behavior for the attributes of certain entity kinds.
    """
    KIND = ''

    def __init__(self, entity, attributes):
        self.entity = entity
        self._attributes = attributes
        self._dynamicProperties = {}
        for attr, prop in self.__class__.__dict__.items():
            if hasattr(prop, '_dynamicProperty') and prop._dynamicProperty:
                self._dynamicProperties[attr] = types.MethodType(
                    prop, self
                    )

    def __len__(self):
        return len(self._attributes)

    def __iter__(self):
        return self._attributes.__iter__()

    def __contains__(self, key):
        return key in self._attributes

    def __getitem__(self, key):
        """Override for custom behavior."""
        if key in self._dynamicProperties:
            return self._dynamicProperties[key]()
        else:
            return self._attributes.__getitem__(key)

    def __setitem__(self, key, value):
        """Override for custom behavior."""
        return self._attributes.__setitem__(key, value)

    def __delitem__(self, key):
        """Override for custom behavior."""
        return self._attributes.__delitem__(key)

    def __repr__(self):
        return '{clsname}: Hook for kind {kind}, attributes {attrs}'.format(
            clsname=self.__class__.__name__,
            kind=self.__class__.KIND,
            attrs=self.attributes
            )

    def copy(self):
        return self._attributes.copy()

    @classmethod
    def getHook(cls, kind):
        if cls.KIND == kind:
            return cls
        else:
            for subcls in cls.__subclasses__():
                try:
                    return subcls.getHook(kind)
                except EntityHookNotFoundError:
                    continue
        raise EntityHookNotFoundError(kind)

    @property
    def attributes(self):
        return self._attributes

    @property
    def friendlyName(self):
        if 'friendlyName' in self:
            return self['friendlyName']
        else:
            return self.entity.name

    def dynamicproperty(func):
        func._dynamicProperty = True
        return func


class RoomEntityHook(EntityHook):
    KIND = "room"

    def __init__(self, entity, attributes):
        super(RoomEntityHook, self).__init__(entity, attributes)
        self.attributes.update(
            time=datetime.datetime(1000, 1, 1)
            )

    @EntityHook.dynamicproperty
    def timeString(self):
        return self.attributes['time'].strftime('%a, %b %d %H:%M')

    @property
    def friendlyName(self):
        name = self.attributes['friendlyName']
        if self.entity.area:
            return ': '.join([self.entity.area.attributes['name'], name])
        else:
            return name


class PlayerEntityHook(EntityHook):
    KIND = "player"

    template = None
    equations = {
        "increasing": {
            "equation": lambda x: 1 / (1 + math.exp(-x)),
            "variance": (-0.1, 0.1),
            "scale": 0.02
            },
        "decreasing": {
            "equation": lambda x: 1 / math.exp(x),
            "variance": (-0.1, 0.1),
            "scale": 0.02
            }
        }

    def __init__(self, entity, attributes):
        super().__init__(entity, attributes)

    def damage(self, magnitude, category, kind, target):
        # XXX category ignored - how to deal with damaged stats?
        if kind is None:
            absorb = 1
        else:
            absorb = random.uniform(*self.stats[kind]['absorb'])
        realDamage = absorb * magnitude
        self.vitals[target] -= realDamage
        if self.vitals[target] < 0:
            self.vitals[target] = 0
        elif self.vitals[target] > self.maxVitals[target]:
            self.vitals[target] = self.maxVitals[target]
        return realDamage

    @property
    def friendlyName(self):
        return self.character['name']

    @property
    def character(self):
        return self.attributes['character']

    @property
    def inventory(self):
        return self.attributes['inventory']

    @property
    def equip(self):
        return self.attributes['equip']

    @property
    def acumen(self):
        return self.attributes['acumen']

    @property
    def vitals(self):
        return self.attributes['vitals']

    @property
    def maxVitals(self):
        res = {}
        for vital, multipliers in self.attributes['maxVitals'].items():
            res[vital] = round(sum(
                    multiplier * abs(acumen) for multiplier, acumen in
                    zip(multipliers, sorted(self.acumen.values()))))
        return res

    @property
    def stats(self):
        allStats = collections.defaultdict(dict)
        template = self.__class__.template.attributes['stats']['template']
        for acumenName, acumenSkill in self.acumen.items():
            for statName, statType in template.items():
                eqData = self.__class__.equations[statType]
                baseStat = eqData['equation'](acumenSkill * eqData['scale'])
                allStats[acumenName][statName] = [baseStat * (1 + v) for v
                                                  in eqData['variance']]
        return allStats

    def describe(self):
        return 'You are {name}, a {gender}: {description}'.format(
            **self.character
              )


class Entity(object):
    def __init__(self, name, kind, attributes={}):
        """
        :param name: The name of the entity (the key in the datastore)
        :param kind: The entity's kind (enemy, door, object, etc.)
        :param attributes: The attributes for the entity (data).

        Change the type of an entity when it needs special
        loading/processing, as with a room, but the kind otherwise.
        """
        self.name = name
        self.kind = kind
        try:
            kindhook = EntityHook.getHook(kind)
            self._attributes = kindhook(self, attributes)
        except EntityHookNotFoundError:
            self._attributes = attributes

    def copy(self):
        """Shallow-copy the entity: copy the attributes."""
        return Entity(self.name, self.kind, self.attributes.copy())

    # no staticmethod() declaration needed! it causes problems anyways...
    def override(func):
        """
        Decorator to replace a method with a hook's method upon first call.

        A method decorated with this will be replaced by a function closure
        containing the original method. When this closure is called, it will
        check to see if the class has an entity kind hook. If there is one,
        and the hook has a method with the same name as the decorated
        method, the hook method will replace the closure and be called.
        Else, the original method will replace the closure and be called.
        """
        funcname = func.__name__

        def _proxy(self, *args, **kwargs):
            if issubclass(self._attributes.__class__, EntityHook):
                if hasattr(self._attributes, funcname):
                    setattr(self, funcname,
                            getattr(self._attributes, funcname))
                else:
                    setattr(self, funcname, types.MethodType(func, self))
            else:
                setattr(self, funcname, types.MethodType(func, self))
            return getattr(self, func.__name__)(*args, **kwargs)
        _proxy.__name__ = func.__name__
        return _proxy

    @override
    def describe(self):
        return self.attributes.get('describe', 'No description.')

    @property
    def friendlyName(self):
        """The entity name for display purposes, defaults to name."""
        return self.attributes.friendlyName

    @property
    def attributes(self):
        return self._attributes

    @attributes.setter
    def attributes(self, value):
        self._attributes.update(value)

    @property
    def entityCache(self):
        """
        The datastore/cache this entity is located in.

        .. warning:: Do NOT use this directly; use :py:meth:`Room.entityFor`
                     instead in most cases.
        """
        return self._entityCache

    @entityCache.setter
    def entityCache(self, cache):
        self._entityCache = cache


EntityData = collections.namedtuple(
    'EntityData',
    'objectLocation key location description prefix options'
    )


class EntityKey(collections.namedtuple('EntityKey', 'key prefix')):
    def __str__(self):
        return ' '.join([self.prefix, self.key])


class Room(Entity):
    ROOM_ENTITY_KIND = 'room'

    def __init__(self, name, description, cache):
        super().__init__(name, Room.ROOM_ENTITY_KIND, {})
        self.entityCache = cache
        self._entityCopies = {}
        self._description = description
        self._contents = {}
        self._outputs = {}
        self.area = None

    def naturalFind(self, text):
        """
        Attempt to find an entity key based on a variety of criteria.

        If there is no unique entity matched, return a set of all possible
        matches. Else, return the only match. Returns None if there is no
        match.

        This method is case-insensitive.
        """
        criteria = [word.strip().lower() for word in text.split()]
        matches = set()
        for eKey in self.contents:
            prefix = [word.strip().lower() for word in eKey.prefix.split()]
            key = [word.strip().lower() for word in eKey.key.split()]
            prefixLength, keyLength = len(prefix), len(key)
            # 2 cases: only identity, or prefix-identity
            if len(criteria) < prefixLength + keyLength:
                # in this case, only identity
                if criteria == key:
                    matches.add(eKey)
            else:
                if (criteria[:prefixLength] == prefix and
                    criteria[prefixLength:] == key):
                    matches.add(eKey)
        if not matches:
            return None
        elif len(matches) == 1:
            return matches.pop()
        else:
            return matches

    def add(self, entityLocation, key,
            location='', description='', prefix='', options=None):
        """
        Add an entity or output to the room.

        :param entityLocation: The entity object's location
                               (e.g. data.items.entity_name).
        :param key: The key for the entity.
        :param location: The location description for the entity.
        :param description: A description of the entity.
        :param options: Options for the entity.
        """
        options = [] if options is None else options
        self._contents[key] = EntityData(
            entityLocation, key, location,
            description, prefix, options)

    def addRoom(self, direction, target):
        self._outputs[direction] = target

    def remove(self, key):
        del self._contents[key]

    def entityFor(self, key):
        if key not in self._entityCopies:
            loc = self.contents[key].objectLocation
            self._entityCopies[key] = self._entityCache.lookup(loc).copy()
        return self._entityCopies[key]

    def describe(self, key=None, verbose=False):
        """
        Describe the specified object, or if not given, the room.
        """
        if key:
            entity = self.allContents[key]
            if key in self.contents:
                if verbose:
                    entity = self.entityFor(key)
                    return entity.describe()
                else:
                    text = 'There is {identity}{location}.'.format(
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
                [self.describe(key) for key in sorted(self.outputs)])

    def enter(self, elapsedTime):
        self.attributes['time'] = elapsedTime

    def exit(self):
        return self.attributes['time']

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
