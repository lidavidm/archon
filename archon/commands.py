import sys
import difflib


class CommandNotFoundError(Exception): pass


class command(object):
    """
    Denote a function as an command.
    """
    # IDEA use this to store global variables for commands (help strings,
    # game name, etc)?
    commands = {}

    def __init__(self, *names):
        for name in names:
            if name in self.__class__.commands:
                raise ValueError(
                    "Command name {} already in use!".format(name)
                    )
        self.names = names

    def __call__(self, func):
        for name in self.names:
            self.__class__.commands[name] = func
        return func

    @classmethod
    def get(cls, name):
        try:
            return cls.commands[name]
        except KeyError:
            raise CommandNotFoundError

    @classmethod
    def nearest(cls, name):
        return difflib.get_close_matches(name, cls.commands.keys())


@command('test.restart')
def test(output, context, player, *args):
    '''Restart the Archon session, if possible. This is a test command.'''
    output.restart()
    return context


@command('go')
def go(output, context, player, *args):
    '''Go in the specified direction.'''
    direction = args[0]  # XXX multiword directions?
    target = context.outputs.get(direction)
    if target:
        context.exit()
        target.enter()
        return target
    else:
        output.error("You can't go that way.")


@command('enter')
def enter(output, context, player, *args):
    '''If the specified entity is a teleport (e.g. a door), use it.'''
    # find the next room, somehow
    context.exit()
    target.enter()
    return target()


@command('describe')
def describe(output, context, player, *args):
    '''Describe the current room or the specified object.'''
    if args:
        matches = context.naturalFind(' '.join(args))
        if not matches:
            output.display("What are you talking about?")
        elif isinstance(matches, set):
            output.error("That was ambiguous.")
            output.display("Did you mean:")
            for match in matches:
                edata = context.contents[match]
                output.display("\t{prefix}{identity}".format(
                    prefix=edata[4] + ' ',
                    identity=edata[1]
                    ))
        else:
            output.display(context.describe(matches))
    else:
        output.display(context.describe())
    return context


@command('quit', 'test.exit')
def quit(output, context, player, *args):
    output.quit()
    return context


@command('help')
def help(output, context, player, *args):
    '''Provides help to the player.'''
    if args:
        try:
            output.display(
                trimDocstring(
                    command.get(args[0]).__doc__
                    )
                )
        except CommandNotFoundError:
            output.error('Command {} not found!'.format(args[0]))
            close = command.nearest(args[0])
            if close:
                output.display('Did you mean: {}'.format(close[0]))
    else:
        output.display(STRING_HELP)


def trimDocstring(docstring):
    '''
    Trim the whitespace in a docstring as per PEP257.

    The contents of PEP257, from which this function was taken, are in the
    public domain.
    '''
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


STRING_HELP = '''
Welcome to the Archon demo. Type 'help [name]' for help on a specific
command or topic.
'''
