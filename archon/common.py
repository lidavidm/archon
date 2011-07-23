import copy
import blinker


def signal(name):
    return blinker.signal(name)


class DenotedNotFoundError(Exception): pass


class DenotedInvalidError(Exception): pass


class denoter:
    """Denote a function as something."""
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
        try:
            return cls.functions[name]
        except KeyError:
            raise DenotedNotFoundError


class Merge:
    """
    Merge two dictionaries together using a patch dictionary.

    This does not support dictionaries nested within lists, or patching
    lists (they are treated as atomic values as strings and numbers are).
    """
    def __init__(self, source, dest=None, patch=None, unsafe=False):
        self.source = source
        self.dest = self.patch = None
        if dest:
            if unsafe:
                self.dest = dest
            else:
                self.dest = copy.deepcopy(dest)
        if patch:
            self.patch = patch

    def result(self, redo=False):
        """Apply the patch to a deepcopy of the source object."""
        if not redo and self.dest:
            return self.dest
        self.dest = copy.deepcopy(self.source)
        stack = [Merge(self.source[key], self.dest[key],
                       patch=patch, unsafe=True)
                 for key, patch in self.patch.items()]
        while stack:
            merge = stack.pop()
            for key, value in merge.created.items():
                merge.dest[key] = value
            for key in merge.deleted:
                del merge.dest[key]
            for key, patch in merge.updated.items():
                stack.append(
                    Merge(merge.source[key], merge.dest[key], patch=patch,
                          unsafe=True))
        return self.dest

    def patch(self):
        """Create a patch from a source and destination."""

    @property
    def created(self):
        return self.patch.get("create", {})

    @property
    def deleted(self):
        return self.patch.get("delete", [])

    @property
    def updated(self):
        return self.patch.get("update", {})
