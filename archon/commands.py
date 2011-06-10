import re
import sys
import ast
import difflib
import collections

import archon.common


class command(archon.common.denoter):
    """
    Denote a function as an command.
    """
    commandData = collections.defaultdict(None)

    @property
    def data(self):
        return self.__class__.commandData[self.names[0]]

    @classmethod
    def nearest(cls, name):
        return difflib.get_close_matches(name, list(cls.functions.keys()))


def find(output, context, player, *args):
    if ' '.join(args) in ('me', 'myself'):
        return player
    matches = context.naturalFind(' '.join(args))
    if not matches:
        output.error('No entity found.')
    elif isinstance(matches, set):
        output.error('Please be more specific.')
    else:
        entity = context.allContents[matches][0]
        entity = context.entityCache[entity]
        return entity
    return None


@command('test.restart')
def test(output, context, player, *args):
    '''Restart the Archon session, if possible. This is a test command.'''
    output.restart()
    return context


useFunctionRe = re.compile(
    r'(?P<function>[a-zA-Z0-9]+)\((?P<arguments>[\S]+)\)'
    )


@command('use')
def use(output, context, player, *args):
    '''Use an object.'''
    item = find(output, context, player, *args)
    if not item or not 'use' in item.attributes:
        output.error("You can't use that.")
        return context
    usage = item.attributes['use']
    result = useFunctionRe.match(usage)
    if result:
        result = result.groupdict()
        function, arguments = result['function'], result['arguments']
        arguments = [ast.literal_eval(x.strip())
                     for x in arguments.split(',')]
        # this is hardcoded since it's the only one supported now
        # currently, it simply runs the script with some globals
        # in the future, an entity should specify what functions in the
        # script should be run, e.g. function(script, functionName)
        # idea: use function annotations to determine which argument
        # represents which desired object
        if function == 'script':
            script = context.entityCache.root[arguments[0]]
            namespace = {'output': output,
                         'context': context,
                         'player': player}
            try:
                exec(script, namespace)
                if 'elapsedTime' in namespace:
                    context.attributes['time'] += namespace['elapsedTime']
            except:  # yes, everything
                output.error("It doesn't work.")
        else:
            output.error("It doesn't work.")
    else:
        output.error("You can't use that.")
    return context


@command('go')
def go(output, context, player, *args):
    '''Go in the specified direction.'''
    direction = args[0]  # XXX multiword directions?
    target = context.outputs.get(direction)
    if target:
        target.enter(context.exit())
        return command.get('describe')(output, target, player)
    else:
        output.error("You can't go that way.")
        return context


@command('enter')
def enter(output, context, player, *args):
    '''
    If the specified entity is a teleport (e.g. a door), use it.

    Also, create an entry in the history chain of visited rooms.
    '''
    teleport = context.naturalFind(' '.join(args))
    if not teleport:
        output.error('No entity found.')
    elif isinstance(teleport, set):
        output.error('Please be more specific.')
    else:
        entityData = context.allContents[teleport]
        for option in entityData.options:
            if option.startswith('to:'):
                target = option[3:].strip()
                target = context.entityCache[target]
                if output.question(
                    "Go to {}?".format(target.attributes['friendlyName'])
                    ):
                    target.enter(context.exit())
                    return command.get('describe')(output, target, player)
    return context  # we failed teleporting


@command('exit', 'back')
def exit(output, context, player, *args):
    '''
    Return to the previous room, unless the history chain was reset.
    '''


@command('describe')
def describe(output, context, player, *args):
    '''Describe the current room or the specified object.'''
    if args:
        if args[0].lower() in ('me', 'myself'):
            output.display(player.describe())
            return context
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
            output.display(context.describe(matches, verbose=True))
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
                trimDocstring(command.get(args[0]).__doc__)
                )
        except CommandNotFoundError:
            output.error('Command {} not found!'.format(args[0]))
            close = command.nearest(args[0])
            if close:
                output.display('Did you mean: {}'.format(close[0]))
    else:
        output.display(STRING_HELP)
    return context


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
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
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
command or topic. If you're just starting, try 'describe' to see what your
area is like.
'''
