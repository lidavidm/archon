import math
import copy
import types
import random
import datetime
import collections

import archon.common
import archon.templating

from archon.entity import (Entity, EntityHook, EntityHookNotFoundError,
                           MutableEntityHook)


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


class InventoryProxy:
    """
    Stores inventory information in a dictionary.

    The keys are the locations of the entities. If the entity kind is
    mutable, then the value is a list of entities; else, it is a count
    denoting the quantity held.
    """
    def __init__(self, items, cache):
        self.inventory = {}
        self.cache = cache

        for path, values in items.items():
            path = cache.fullPathFor(path)
            self.inventory[path] = values

    def add(self, item, quantity=1):
        if isinstance(item, Entity):
            if item.mutable:
                if item.location not in self.inventory:
                    self.inventory[item.location] = []
                self.inventory[item.location].append(item)
            else:
                if item.location not in self.inventory:
                    self.inventory[item.location] = 0
                self.inventory[item.location] += 1
        else:
            item = self.cache.fullPathFor(item)
            if item not in self.inventory:
                self.inventory[item] = 0
            self.inventory[item] += 1

    def remove(self, item, quantity='all'):
        if isinstance(item, Entity):
            pass

    def locations(self):
        """Iterate through the entity locations of held items."""
        pass

    def counts(self):
        """Iterate through the counts of held items."""
        pass

    def entities(self):
        """Iterate through the 3-tuples (location, count, instances).

        If the entity is immutable, ``instances`` will be a one-item
        list. Else, it will be the list of entity instances."""
        pass

    def save(self):
        pass


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
        self.inventory = InventoryProxy(attributes['inventory'], cache)

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
        for entity, count in self.attributes['inventory'].items():
            # TODO save inventory
            pass
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
        """Return the inventory."""
        return self.inventory

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
            prefix='', messages='third_person_neutral',
            options=None, instance=None):
        """
        Add an entity or output to the room.

        :param entityLocation: The entity object's location
                               (e.g. data.items.entity_name).
        :param key: The key for the entity.
        :param location: The location description for the entity.
        :param description: A description of the entity.
        :param messages: The messages for the entity's description.
        :param options: Options for the entity.
        :param instance: An instance of the entity.
        """
        options = [] if options is None else options
        if isinstance(messages, str):
            messages = self.entityCache.lookup(messages)
        assert isinstance(messages, Entity)
        self._contents[key] = EntityData(
            entityLocation, key, location,
            description, prefix, messages, options)
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
                    messages = entity.messages.attributes
                    text = [messages.message('summary', entityData=entity)]
                    if entity.description:
                        text.append(messages.message('description',
                                                     entityData=entity))
                    return ' '.join(text)
                    # text = 'There is {identity}{location}.'.format(
                    #     identity=entity[1],
                    #     location=' ' + entity[2] if entity[2] else ''
                    #     ).strip()
                    # if entity[3]:
                    #     text = ' '.join([text, 'It is', entity[3] + '.'])
                    # return text
            elif key in self.outputs:
                return 'You can go {}.'.format(key)
        else:
            outputs = 'Adjoining areas: ' + ', '.join(self.outputs)
            return '\n'.join(
                ['You are in ' + self._description] +
                [self.describe(key) for key in sorted(self.contents)] +
                [outputs])

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


class EntityData(collections.namedtuple(
    'EntityData',
    'objectLocation key location description prefix messages options'
    )):
    """
    Contains the metadata used by a room to describe an entity.
    """
    def save(self):
        """Saves the metadata."""
        data = {key: val for key, val in self._asdict().items() if val}
        data['entity'] = data['objectLocation']
        data['messages'] = data['messages'].location
        del data['objectLocation'], data['key']
        if 'prefix' in data:
            del data['prefix']
        if 'options' in data:
            data['options'] = ','.join(data['options'])
        return data


class UnionDict(dict):
    def __init__(self, *dicts):
        self._dicts = dicts

    def __getitem__(self, key):
        for dictionary in self._dicts:
            if key in dictionary:
                return dictionary[key]
        raise KeyError(key)
