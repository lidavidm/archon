import copy
import collections


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
