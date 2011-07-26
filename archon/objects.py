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
    KIND = ''
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
        return self

    def save(self):
        return self.attributes.copy()

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
    def description(self):
        return 'No description.'

    @property
    def friendlyName(self):
        if 'friendlyName' in self:
            return self['friendlyName']
        else:
            return self.entity.name

    def viaTemplate(self, attributes):
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
    mutable = True

    def copy(self):
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


class AttributeDict(dict):
    def __getattr__(self, key):
        if key in self:
            item = self[key]
            if isinstance(item, dict):
                return AttributeDict(item)
            return item
        raise AttributeError(key)


class MessageTemplateEntityHook(EntityHook):
    KIND = "message_template"

    def __getitem__(self, key):
        item = super().__getitem__(key)
        if isinstance(item, dict):
            return AttributeDict(item)
        return item


class PlayerEntityHook(MutableEntityHook):
    KIND = "player"

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
        return cls.templates['default'].copy(instanced=False)

    def damage(self, magnitude, category, kind, target):
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
    def level(self):
        return math.floor(sum(abs(x) for x in self.acumen.values()) / 100)

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
    instances = None

    def __init__(self, name, kind, cache, attributes={}, prototype=None):
        """
        :param name: The name of the entity (the key in the datastore)
        :param kind: The entity's kind (enemy, door, object, etc.)
        :param attributes: The attributes for the entity (data).

        Change the type of an entity when it needs special
        loading/processing, as with a room, but the kind otherwise.
        """
        self.name = name
        self.kind = kind
        self.entityCache = cache
        self.prototype = prototype
        if issubclass(attributes.__class__, EntityHook):
            self._attributes = attributes
        else:
            try:
                kindhook = EntityHook.getHook(kind)
                self._attributes = kindhook(self, attributes)
            except EntityHookNotFoundError:
                self._attributes = EntityHook(self, attributes)

    def copy(self, instanced=True):
        """Perform a shallow copy if mutable, else return self.

        If instanced is `True`, then the copy will be placed in
        Entity.instances under the datastore with the same name as the
        entity kind."""
        if self.mutable:
            attributes = self.attributes.copy()
            if instanced:
                if self.kind not in Entity.instances:
                    Entity.instances.create(self.kind)
                instances = Entity.instances[self.kind]
                if instances:
                    newName = max(int(key) for key in instances.keys()) + 1
                else:
                    newName = 0
                entity = Entity(
                    str(newName), self.kind, self.entityCache,
                    attributes, prototype=self)
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
        return self.attributes.description

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

    @property
    def location(self):
        return '.'.join([self.entityCache.fullName, self.name])

    @property
    def mutable(self):
        return self.attributes.mutable and not self.prototype

    def __repr__(self):
        return "<Entity '{}' name={} kind={}>".format(
            self.friendlyName, self.name, self.kind)


class EntityData(collections.namedtuple(
    'EntityData',
    'objectLocation key location description prefix options'
    )):
    def save(self):
        data = {key: val for key, val in self._asdict().items() if val}
        data['entity'] = data['objectLocation']
        del data['objectLocation']
        if 'prefix' in data:
            del data['prefix']
        if 'options' in data:
            data['options'] = ','.join(data['options'])
        return data


class EntityKey(collections.namedtuple('EntityKey', 'key prefix')):
    def __str__(self):
        return ' '.join([self.prefix, self.key])

    def save(self):
        return ', '.join([self.key, self.prefix])


class Room(Entity):
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
        self._outputs[direction] = target

    def remove(self, key):
        del self.contents[key]
        del self._entityCopies[key]

    def clearContents(self):
        self.contents.clear()
        self._entityCopies.clear()

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
        self.attributes['time'] = elapsedTime
        self.onEnter.send(self)

    def exit(self):
        return self.attributes['time']

    def copy(self):
        return self  # Rooms are mutable singletons

    def save(self):
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
