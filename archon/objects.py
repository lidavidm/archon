import math
import copy
import types
import random
import datetime
import collections

import archon.common


class EntityHookNotFoundError(Exception): pass


class EntityHook(collections.Mapping):
    """
    Defines special behavior for the attributes of certain entity kinds.
    """

    """The `kind` of the entity."""
    KIND = ''

    """The templates for this entity kind."""
    templates = {}
    mutable = False

    def __init__(self, entity, attributes):
        self.entity = entity
        self._attributes = attributes

    def __len__(self):
        return len(self._attributes)

    def __iter__(self):
        return self._attributes.__iter__()

    def __contains__(self, key):
        return key in self._attributes

    def __getitem__(self, key):
        """Override for custom behavior."""
        return self._attributes.__getitem__(key)

    def __setitem__(self, key, value):
        """Override for custom behavior."""
        return self._attributes.__setitem__(key, value)

    def __delitem__(self, key):
        """Override for custom behavior."""
        return self._attributes.__delitem__(key)

    def __repr__(self):
        return '{clsname}: Hook for {kind}'.format(
            clsname=self.__class__.__name__,
            kind=self.__class__.KIND)

    def copy(self):
        """
        Create a copy of the attributes in the entity hook.

        By default, hooks are immutable, and so this method simply returns
        self.
        """
        return self

    def save(self):
        """
        Create a saveable copy of the attributes.
        """
        return self.attributes.copy()

    @classmethod
    def getHook(cls, kind):
        """
        Find an entity hook based on class kind.
        """
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
    def description(self):
        """ Return the description of this entity. """
        return 'No description.'

    @property
    def friendlyName(self):
        """Return a user-friendly name for this entity."""
        if 'friendlyName' in self:
            return self['friendlyName']
        else:
            return self.entity.name

    def viaTemplate(self, attributes):
        """Format attributes using this entity as a template."""
        # TODO use archon.common.Merge
        result = copy.deepcopy(self.attributes)
        stack = [(result, attributes)]
        while stack:
            dst, src = stack.pop()
            for key, data in src.items():
                if isinstance(data, dict):
                    if key not in dst:
                        dst[key] = {}
                    stack.append((dst[key], data))
                else:
                    dst[key] = data
        return result


class MutableEntityHook(EntityHook, collections.MutableMapping):
    """
    A mutable entity hook.
    """
    mutable = True

    def copy(self):
        """
        Returns a shallow-copy of the attributes dictionary.
        """
        return self.attributes.copy()


class RoomEntityHook(MutableEntityHook):
    KIND = "room"

    def __init__(self, entity, attributes):
        super(RoomEntityHook, self).__init__(entity, attributes)
        self.attributes.update(
            time=datetime.datetime(1000, 1, 1)
            )

    @property
    def timeString(self):
        return self.attributes['time'].strftime('%a, %b %d %H:%M')

    @property
    def friendlyName(self):
        name = self.attributes['friendlyName']
        if self.entity.area:
            return ': '.join([self.entity.area.attributes['name'], name])
        else:
            return name

    def save(self):
        data = self.attributes.copy()
        del data['time']
        return data


class TemplatingDict(dict):
    def __init__(self, dictionary, **kwargs):
        dictionary.update(kwargs)
        super().__init__(dictionary)
        self.kwargs = kwargs

    def __getattr__(self, key):
        if key.endswith('_capitalized'):
            return super().__getitem__(key[:-12]).capitalize()
        elif key in self:
            item = super().__getitem__(key)
            if isinstance(item, dict):
                return TemplatingDict(item, **self.kwargs)
            elif isinstance(item, str) and '{' in item and '}' in item:
                return item.format(**self)
            return item
        raise AttributeError(key)

    __getitem__ = __getattr__


class MessageTemplateEntityHook(EntityHook):
    KIND = "message_template"
    templates = {}

    def __init__(self, entity, attributes):
        super().__init__(entity, attributes)
        for key, template in attributes.items():
            MessageTemplateEntityHook.templates[key] = template

    @classmethod
    def format(cls, mode, text, *args, **kwargs):
        return text.format(*args, **cls.template(mode, **kwargs))

    @classmethod
    def template(cls, key, **kwargs):
        item = cls.templates[key]
        if isinstance(item, dict):
            return TemplatingDict(item, **kwargs)
        return item


class PlayerEntityHook(MutableEntityHook):
    KIND = "player"

    """The equations used to calculate stats based on acumen."""
    equations = {
        "increasing": {
            "equation": lambda x: 1 / (1 + math.exp(-x)),
            "variance": (-0.3, 0.05),
            "scale": 0.007
            },
        "decreasing": {
            "equation": lambda x: 1 / math.exp(x),
            "variance": (-0.05, 0.3),
            "scale": 0.007
            }
        }

    def __init__(self, entity, attributes):
        if self.templates:
            attributes = self.templates['default'].attributes.viaTemplate(
                attributes)
        super().__init__(entity, attributes)
        # Load inventory, equip, etc. from data
        cache = entity.entityCache
        for slot, location in attributes['equip'].items():
            # can be None - no item equipped, or an entity, because I might
            # be a copy of an entity that already loaded the equipped items
            if isinstance(location, str):
                attributes['equip'][slot] = cache.lookup(location)
        inventory = attributes['inventory']
        attributes['inventory'] = []
        for location in inventory:
            if isinstance(location, str):
                attributes['inventory'].append(cache.lookup(location))
            else:
                attributes['inventory'].append(location)

    @classmethod
    def defaultInstance(cls):
        """Return the default instance of the player."""
        return cls.templates['default'].copy(instanced=False)

    def damage(self, magnitude, category, kind, target):
        """Damage a vital or stat of this player.

        :param magnitude: Amount of damage (use negative to heal).
        :param category: Either `'vital'` or `'stat'`.
        :param kind: Either an acumen type, or None, used to determine
                     absorption amount.
        :param target: Either a vital or stat name."""
        # XXX category ignored - how to deal with damaged stats?
        if kind is None:
            absorb = 0
        else:
            absorb = random.uniform(*self.stats[kind]['absorb'])
        realDamage = magnitude - (absorb * magnitude)
        self.vitals[target] -= realDamage
        if self.vitals[target] < 0:
            self.vitals[target] = 0
        elif self.vitals[target] > self.maxVitals[target]:
            self.vitals[target] = self.maxVitals[target]
        return realDamage

    def save(self):
        data = super().save()
        for slot, entity in self.attributes['equip'].items():
            if entity:
                data['equip'][slot] = entity.location
        return data

    @property
    def friendlyName(self):
        return 'You'  # self.character['name']

    @property
    def character(self):
        """Return the character information dictionary."""
        return self.attributes['character']

    @property
    def inventory(self):
        """Return the inventory list."""
        return self.attributes['inventory']

    @property
    def equip(self):
        """The equip dictionary."""
        return self.attributes['equip']

    @property
    def acumen(self):
        """The acumen dictionary."""
        return self.attributes['acumen']

    @property
    def vitals(self):
        """The vitals dictionary."""
        return self.attributes['vitals']

    @property
    def level(self):
        """The level of the character."""
        return math.floor(sum(abs(x) for x in self.acumen.values()) / 100)

    @property
    def maxVitals(self):
        """The maximum vital amount."""
        res = {}
        for vital, multipliers in self.attributes['maxVitals'].items():
            res[vital] = round(sum(
                    multiplier * abs(acumen) for multiplier, acumen in
                    zip(multipliers, sorted(self.acumen.values()))))
        return res

    @property
    def stats(self):
        """The stats dictionary."""
        allStats = collections.defaultdict(dict)
        template = self.templates['default'].attributes['stats']['template']
        for acumenName, acumenSkill in self.acumen.items():
            for statName, statType in template.items():
                lbC = ubC = 0  # lower bound, upper bound constant terms
                if isinstance(statType, list):
                    statType, lbC, ubC = statType
                eqData = self.__class__.equations[statType]
                baseStat = eqData['equation'](acumenSkill * eqData['scale'])
                allStats[acumenName][statName] = [
                    c + (baseStat * (1 + v)) for v, c
                    in zip(eqData['variance'], [lbC, ubC])]
        return allStats

    @property
    def description(self):
        desc = 'You are {name}, a {gender} of level {level}: {description}'
        return (desc.format(level=self.level, **self.character))


class Entity(object):
    """
    The basic game object.

    Entities are usually not directly modified unless they have been copied
    first. When an entity is used in a room, a copy is created for that
    particular area. This copy is stored in a different location in the
    datastore: it is stored in the same datastore as the player under a
    sub-datastore named "instances".
    """

    """The instances datastore in the player's datastore."""
    instances = None

    def __init__(self, name, kind, cache, attributes={}, prototype=None,
                 location=None):
        """
        :param name: The name of the entity (the key in the datastore)
        :param kind: The entity's kind (enemy, door, object, etc.)
        :param attributes: The attributes for the entity (data).
        :param prototype: The prototype of this entity.
        :param location: If given, an alternate location in the datastore
                         for the entity (used for instances).

        Change the type of an entity when it needs special
        loading/processing, as with a room, but the kind otherwise.
        """
        self.name = name
        self.kind = kind
        self.entityCache = cache
        self.prototype = prototype
        self._location = location if location else cache
        if issubclass(attributes.__class__, EntityHook):
            self._attributes = attributes
        else:
            try:
                kindhook = EntityHook.getHook(kind)
                self._attributes = kindhook(self, attributes)
            except EntityHookNotFoundError:
                self._attributes = EntityHook(self, attributes)

    def copy(self, instanced=True, name=None, attributes=None):
        """Perform a shallow copy if mutable, else return self.

        :param instanced: If `True`, place the copy in Entity.intstances
                          under the datastore named after the entity kind.
        :param name: (Implementation parameter.) Specify the name of the
                     entity copy.
        :param attributes: (Implementation parameter.) Specify the
                           attribute dictionary of the copy.
        """
        if self.mutable:
            attributes = attributes if attributes else self.attributes.copy()
            if instanced:
                if self.kind not in Entity.instances:
                    Entity.instances.create(self.kind)
                instances = Entity.instances[self.kind]
                if name:  # datahandlers - loading an instance
                    newName = name
                elif instances:
                    newName = max(int(key) for key in instances.keys()) + 1
                else:
                    newName = 0
                entity = Entity(
                    str(newName), self.kind, self.entityCache,
                    attributes, prototype=self,
                    location=instances)
                instances.add(entity.name, entity)
                print("Created instance of", self.name)
                return instances[str(newName)]
            else:
                return Entity(self.name + '_copy', self.kind,
                              self.entityCache, attributes, prototype=self)
        else:
            return self

    def __deepcopy__(self, memo):
        return self.copy()

    def save(self):
        """Return a dictionary containing all data to serialize."""
        return {
            "type": "entity",
            "data": {
                "kind": self.attributes.KIND,
                "attributes": self.attributes.save()
            }
        }

    @property
    def description(self):
        """The description for the entity."""
        return self.attributes.description

    @property
    def friendlyName(self):
        """The entity name for display purposes; defaults to name."""
        return self.attributes.friendlyName

    @property
    def attributes(self):
        """The attributes dictionary or entity hook."""
        return self._attributes

    @attributes.setter
    def attributes(self, value):
        self._attributes.update(value)

    @property
    def entityCache(self):
        """
        The datastore/cache this entity is located in.

        .. warning:: Do NOT use this directly; use :meth:`Room.entityFor`
                     instead in most cases.
        """
        return self._entityCache

    @entityCache.setter
    def entityCache(self, cache):
        self._entityCache = cache

    @property
    def location(self):
        """The location of this entity in the datastore."""
        return '.'.join([self._location.fullName, self.name])

    @property
    def mutable(self):
        """Returns whether this entity is mutable or not."""
        return self.attributes.mutable and not self.prototype

    def __repr__(self):
        return "<Entity '{}' name={} kind={}>".format(
            self.friendlyName, self.name, self.kind)


class EntityData(collections.namedtuple(
    'EntityData',
    'objectLocation key location description prefix options'
    )):
    """
    Contains the metadata used by a room to describe an entity.
    """
    def save(self):
        """Saves the metadata."""
        data = {key: val for key, val in self._asdict().items() if val}
        data['entity'] = data['objectLocation']
        del data['objectLocation'], data['key']
        if 'prefix' in data:
            del data['prefix']
        if 'options' in data:
            data['options'] = ','.join(data['options'])
        return data


class EntityKey(collections.namedtuple('EntityKey', 'key prefix')):
    """Contains the entity's name and its "prefix" (a, an, another, etc.)"""
    def __str__(self):
        return ' '.join([self.prefix, self.key])

    def save(self):
        return ', '.join([self.key, self.prefix])


class Room(Entity):
    """
    The basic room type, a special-cased :class:`Entity`.

    Rooms contain other entities. All player movement and interaction occurs
    within rooms; however, rooms do not contain the actual entity objects,
    simply metadata to describe them. When an interaction occurs, a copy is
    created of the object and is stored in a room-specific cache.
    """
    ROOM_ENTITY_KIND = 'room'
    onEnter = archon.common.signal('room.enter')

    def __init__(self, name, description, cache):
        super().__init__(name, Room.ROOM_ENTITY_KIND, cache, {})
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

    def add(self, entityLocation, key, location='', description='',
            prefix='', options=None, instance=None):
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
        if instance:
            self._entityCopies[key] = instance

    def addRoom(self, direction, target):
        """Add an exit to this room."""
        self._outputs[direction] = target

    def remove(self, key):
        """Remove an entity from this room."""
        del self.contents[key]
        del self._entityCopies[key]

    def clearContents(self):
        """Clear the contents of this room."""
        self.contents.clear()
        self._entityCopies.clear()

    def entityFor(self, key):
        """Retrieve or create a copy of an entity in this room."""
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
                    return entity.description
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
        """Enter the room at the given time."""
        self.attributes['time'] = elapsedTime
        self.onEnter.send(self)

    def exit(self):
        """Exit the room.

        :returns: datetime -- The current time
        """
        return self.attributes['time']

    def copy(self):
        """Copy the room - this will return the room itself."""
        return self  # Rooms are mutable singletons

    def save(self):
        """Create a saveable representation of the room."""
        res = {"contents": {}, "outputs": {},
               "describe": self._description,
               "attributes": self.attributes.save()}
        for key, data in self.contents.items():
            res["contents"][key.save()] = data.save()
        for direction, target in self.outputs.items():
            res["outputs"][direction] = target.location
        return {"type": "room", "data": res}

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
