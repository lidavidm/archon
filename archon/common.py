class DenotedNotFoundError(Exception): pass


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
        for name in self.names:
            self.__class__.functions[name] = func
        return func

    @classmethod
    def get(cls, name):
        try:
            return cls.functions[name]
        except KeyError:
            raise DenotedNotFoundError
