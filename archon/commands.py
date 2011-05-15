

class command(object):
    """
    Denote a function as an command.
    """
    commands = {}

    def __init__(self, name):
        if name in self.__class__.commands:
            raise ValueError("Command name {} already in use!".format(name))
        self.name = name

    def __call__(self, func):
        self.__class__.commands[self.name] = func
        return func

    @classmethod
    def get(cls, name):
        return cls.commands[name]


@command('test')
def test(context, player, output, *args):
    output.display(''.join(args))
    return context


@command('go')
def go(context, player, output, *args):
    # find the next room, somehow
    context.exit()
    target.enter()
    return target


@command('describe')
def describe(context, player, output, *args):
    if args:
        pass
    else:
        output.display(context.describe())
