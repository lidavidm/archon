import blinker


def signal(name):
    return blinker.signal(name)


class DenotedNotFoundError(Exception): pass


class DenotedInvalidError(Exception): pass


class denoter(object):
    """
    Denote a function as something.
    """
    functions = {}

    def __init__(self, *names):
        for name in names:
            if name in self.__class__.functions:
                raise ValueError(
                    "Name {} already in use!".format(name)
                    )
        self.names = names

    def __call__(self, func):
        valid = self.verify(func)
        if not (valid is True):
            raise DenotedInvalidError(valid)
        for name in self.names:
            self.__class__.functions[name] = func
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
