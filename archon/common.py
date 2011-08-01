import copy
import blinker


def signal(name):
    """Creates an event signal; based on blinker's signal."""
    return blinker.signal(name)


class DenotedNotFoundError(Exception): pass


class DenotedInvalidError(Exception):
    """Some function failed :meth:`denoter.verify`."""


class denoter:
    """
    Decorator to denote a function as having some purpose.

    This class is used as a decorator to associate a list of names with a
    function, which, for example, can be used to denote certain functions as
    commands and provide their command names. Subclass this to provide
    semantic usage information; when doing so, make sure to create a
    `functions` class attribute (or else the attribute of the superclass
    will be used).
    """
    functions = {}

    def __init__(self, *names):
        for name in names:
            if name in self.functions:
                raise ValueError(
                    "Name {} already in use!".format(name)
                    )
        self.names = names

    def __call__(self, func):
        valid = self.verify(func)
        if not (valid is True):
            raise DenotedInvalidError(valid)
        for name in self.names:
            self.functions[name] = func
        return func

    @classmethod
    def contains(cls, func):
        """Checks if this denoter class has a particular function."""
        return func in cls.functions

    def verify(self, func):
        """
        Override to check whether a function meets certain criteria.

        This method must return True. Anything else is treated as the error
        message to raise.
        """
        return True

    @classmethod
    def get(cls, name):
        """Get a particular function."""
        try:
            return cls.functions[name]
        except KeyError:
            raise DenotedNotFoundError


class MergeItemSemigroup:
    def msum(self, orig, new):
        return new

    def mdifference(self, orig, new):
        return new


class NumericItemSemigroup(MergeItemSemigroup):
    def msum(self, orig, new):
        if type(orig) in (int, float) and type(new) in (int, float):
            return new + orig
        return new

    def mdifference(self, orig, new):
        if type(orig) in (int, float) and type(new) in (int, float):
            return new - orig
        return new


class Merge:
    """
    Merge two dictionaries together using a patch dictionary.

    This does not support dictionaries nested within lists, or patching
    lists (they are treated as atomic values as strings and numbers are).
    """
    def __init__(self, source, dest=None, patch=None, unsafe=False,
                 sgroup=MergeItemSemigroup()):
        self.source = source
        self.dest = {}
        self.patch = patch
        self.sgroup = sgroup
        if dest:
            if unsafe:
                self.dest = dest
            else:
                self.dest = copy.deepcopy(dest)
        if patch:
            self.patch = patch

    def patched(self, redo=False):
        """Apply the patch to a deepcopy of the source object."""
        if not redo and self.dest:
            return self.dest
        self.dest = copy.deepcopy(self.source)
        stack = [self]
        while stack:
            merge = stack.pop()
            for key, value in merge.created.items():
                merge.dest[key] = self.sgroup.msum(
                    merge.dest.get(key), value)
            for key in merge.deleted:
                del merge.dest[key]
            for key, patch in merge.updated.items():
                stack.append(
                    Merge(merge.source[key], merge.dest[key], patch=patch,
                          unsafe=True, sgroup=self.sgroup))
        return self.dest

    def compared(self, redo=False):
        """Create a patch from a source and destination."""
        if not redo and self.patch:
            return self.patch
        self.patch = {}
        stack = [self]
        while stack:
            merge = stack.pop()
            for key, data in merge.dest.items():
                if key not in merge.source:
                    merge.create(key, data)
                elif data != merge.source[key]:
                    if type(data) == dict:
                        merge.update(key, {})
                        stack.append(
                            Merge(merge.source[key], data,
                                  patch=merge.patch['update'][key],
                                  sgroup=self.sgroup))
                    else:
                        merge.create(key, data)
            for key in merge.source:
                if key not in merge.dest:
                    merge.delete(key)
        return self.patch

    def create(self, key, data):
        if "create" not in self.patch:
            self.patch["create"] = {}
        self.patch["create"][key] = self.sgroup.mdifference(
            self.source.get(key), data)

    def delete(self, key):
        if "delete" not in self.patch:
            self.patch["delete"] = []
        self.patch["delete"].append(key)

    def update(self, key, data):
        if "update" not in self.patch:
            self.patch["update"] = {}
        self.patch["update"][key] = data

    @property
    def created(self):
        return self.patch.get("create", {})

    @property
    def deleted(self):
        return self.patch.get("delete", [])

    @property
    def updated(self):
        return self.patch.get("update", {})
