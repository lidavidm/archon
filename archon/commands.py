

class CommandNotFoundError(Exception):pass


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
        try:
            return cls.commands[name]
        except KeyError:
            raise CommandNotFoundError


@command('test.restart')
def test(output, context, player, *args):
    output.restart()
    return context


@command('go')
def go(output, context, player, *args):
    # find the next room, somehow
    context.exit()
    target.enter()
    return target


@command('describe')
def describe(output, context, player, *args):
    if args:
        matches = context.naturalFind(''.join(args))
        print matches
        if not matches:
            output.display("What are you talking about?")
        elif isinstance(matches, set):
            output.error("That was ambiguous.")
            output.display("Did you mean:")
            for match in matches:
                edata = context.contents[match]
                output.display("\t{prefix}{identity}".format(
                    prefix=edata[4]+' ',
                    identity=edata[1]
                    ))
        else:
            output.display(context.describe(matches))
    else:
        output.display(context.describe())
    return context
