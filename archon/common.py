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
        self.dest = {}
        self.patch = patch
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
                                  patch=merge.patch['update'][key]))
                    else:
                        merge.create(key, data)
            for key in merge.source:
                if key not in merge.dest:
                    merge.delete(key)
        return self.patch

    def create(self, key, data):
        if "create" not in self.patch:
            self.patch["create"] = {}
        self.patch["create"][key] = data

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
