import re
import sys
import ast
import inspect
import difflib
import traceback
import collections

import archon.common


class command(archon.common.denoter):
    """
    Denote a function as an command.
    """
    commandData = collections.defaultdict(None)

    def __call__(self, func):
        def closure(output, context, player, *args):
            argspec = inspect.getfullargspec(func)
            if argspec.varargs in argspec.annotations:
                args = argspec.annotations[argspec.varargs](
                    output, context, player, *args
                    )
                if not isinstance(args, collections.Iterable):
                    args = [args]
            res = func(output, context, player, *args)
            if not res:
                res = context
            return res

        closure.__name__ = func.__name__
        return super().__call__(closure)

    @property
    def data(self):
        return self.__class__.commandData[self.names[0]]

    @data.setter
    def data(self, value):
        self.__class__.commandData[self.names[0]] = value

    @classmethod
    def nearest(cls, name):
        return difflib.get_close_matches(name, list(cls.functions.keys()))


# XXX always return an iterable - else the closure will wrap it in a list
def find(output, context, player, *args):
    matches = context.naturalFind(' '.join(args))
    if matches is None:
        return []
    elif isinstance(matches, set):
        result = []
        for key in matches:
            entity = context.allContents[key]
            result.append((entity, context.entityFor(key)))
        return result
    else:
        entity = context.allContents[matches]
        return [(entity, context.entityFor(matches))]


def findMulti(output, context, player, *args):
    criteria = [x.strip().split() for x in ' '.join(args).split(',')]
    return sum((find(output, context, player, *crit) for crit in criteria),
               [])


def findInventory(output, context, player, *args):
    '''Lookup an item by friendly name or index.'''
    if not args:
        return []
    criterion = ' '.join(args)
    try:
        criterion = int(criterion)
        return list(sorted(player.attributes.inventory))[criterion]
    except IndexError:
        raise output.error("Invalid index.")
    except ValueError:
        for item in player.attributes.inventory:
            if item.friendlyName == criterion:
                return item
        raise output.error("Item not found.")


def findEquip(output, context, player, *args):
    criterion = ' '.join(args)
    for slot, item in player.attributes.equip.items():
        if item and criterion in (slot, item.friendlyName):
            return slot, item
    return []


@command('vitals')
def vitals(output, context, player, *args):
    values = player.attributes.vitals
    maxVals = player.attributes.maxVitals
    output.display("Health: {}/{}".format(values['health'],
                                          maxVals['health']))
    output.display("AP    : {}/{}".format(values['ap'], maxVals['ap']))


@command('inventory')
def inventory(output, context, player, *args):
    output.display(
        'Inventory ({length})'.format(
            length=len(player.attributes.inventory)
            ))
    for index, item in enumerate(sorted(player.attributes.inventory,
                                        key=lambda k: k.friendlyName)):
        output.display('{}. {}'.format(index, item.friendlyName))
    return context


@command('equip')
def equip(output, context, player, *args: findInventory):
    if not args:
        for slot, item in sorted(player.attributes.equip.items()):
            if item is None:
                item = '<Empty>'
            else:
                item = item.friendlyName
            output.display('{slot}: {item}'.format(
                    slot=slot, item=item
                    ))
    else:
        args = args[0]
        if not args.attributes.get('equip'):
            raise output.error('Cannot equip item.')
        elif (list(player.attributes.equip.values()).count(args) ==
              player.attributes.inventory.count(args)):
            raise output.error('Already equipped all of that item.')
        else:
            possibleSlots = args.attributes['equip']
            equip = player.attributes.equip
            for slot in possibleSlots:
                if slot not in equip or not equip[slot]:
                    equip[slot] = args
                    break
            equip[possibleSlots[0]] = args


@command('unequip')
def unequip(output, context, player, *args: findEquip):
    slot, item = args
    player.attributes.equip[slot] = None
    output.display('Unequipped item {} from {}'.format(
            item.friendlyName, slot))


@command('take')
def take(output, context, player, *item: find):
    if not item:
        output.error("You can't take that.")
    elif len(item) > 1:  # ambiguous reference
        raise output.error("What did you want to take?")
    else:
        data, item = item[0]
        if not item.attributes.get("take", False):
            raise output.error("You can't take that.")
        player.attributes.inventory.append(item)
        del context.contents[data.key]


useFunctionRe = re.compile(
    r'(?P<function>[a-zA-Z0-9]+)\((?P<arguments>[\S]+)\)'
    )


@command('use')
def use(output, context, player, *item: find):
    '''Use an object.'''
    if not item or len(item) > 1:
        raise output.error("What did you want to use?")
    data, item = item[0]
    if not 'use' in item.attributes:
        raise output.error("You can't use that.")
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
            script = context.entityCache.lookup(arguments[0])
            namespace = {'output': output,
                         'context': context,
                         'player': player}
            try:
                exec(script, namespace)
                if 'elapsedTime' in namespace:
                    context.attributes['time'] += namespace['elapsedTime']
            except:  # yes, everything
                output.error("It doesn't work.")
                if output.permissions.get('debug', False):
                    output.error(traceback.format_exc())
        else:
            output.error("It doesn't work.")
    else:
        output.error("You can't use that.")


@command('go')
def go(output, context, player, *args):
    '''Go in the specified direction.'''
    direction = args[0]  # XXX multiword directions?
    target = context.outputs.get(direction)
    if target:
        if target.area != context.area:
            output.display(target.area.describe())
        target.enter(context.exit())
        return command.get('describe')(output, target, player)
    else:
        output.error("You can't go that way.")
        return context


@command('enter')
def enter(output, context, player, *target: find):
    '''
    If the specified entity is a teleport (e.g. a door), use it.

    Also, create an entry in the history chain of visited rooms.
    '''
    if not target or len(target) > 1:
        raise output.error("Where did you want to enter?")
    entityData, entity = target[0]
    for option in entityData.options:
        if option.startswith('to:'):
            target = option[3:].strip()
            target = context.entityCache.lookup(target)
            if output.question(
                "Go to {}? ".format(target.friendlyName)
                ):
                if target.area != context.area:
                    output.display(target.area.describe())
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
    if not args:
        output.display(context.describe())
    elif args[0].lower() in ('me', 'myself'):
        output.display(player.describe())
    else:
        items = find(output, context, player, *args)
        if not items:
            output.error("What did you want to describe?")
        elif len(items) > 1:
            output.error("That was ambiguous. Did you mean:")
            for data, entity in items:
                output.display("\t{prefix} {identity}".format(
                        prefix=data[4],
                        identity=data[1]
                        ))
        else:
            output.display(items[0][1].describe())


@command('quit', 'test.exit')
def quit(output, context, player, *args):
    output.quit()


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
