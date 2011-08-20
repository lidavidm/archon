import re
import sys
import ast
import inspect
import difflib
import datetime
import traceback
import collections

import archon.common
import archon.objects


class command(archon.common.denoter):
    """
    Denote a function as an command.
    """
    functions = {}
    commandData = collections.defaultdict(None)
    preExecute = archon.common.signal('command.preExecute')
    postExecute = archon.common.signal('command.postExecute')

    def __call__(self, func):
        def closure(output, context, player, *args):
            argspec = inspect.getfullargspec(func)
            if argspec.varargs in argspec.annotations:
                args = argspec.annotations[argspec.varargs](
                    output, context, player, *args
                    )
                if not isinstance(args, collections.Iterable):
                    args = [args]
            self.__class__.preExecute.send(self)
            res = func(output, context, player, *args)
            self.__class__.postExecute.send(self)
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
        return list(sorted(player.attributes.inventory,
                           key=lambda k: k.friendlyName))[criterion]
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


@command('me')
def me(output, context, player, *args):
    command.get('describe')(output, context, player, 'me')
    for cmdName in ('vitals', 'stats', 'inventory', 'equip'):
        command.get(cmdName)(output, context, player)


@command('vitals')
def vitals(output, context, player, *args):
    values = player.attributes.vitals
    maxVals = player.attributes.maxVitals
    output.display("Health: {}/{}".format(values['health'],
                                          maxVals['health']))
    output.display("AP    : {}/{}".format(values['ap'], maxVals['ap']))


@command('stats')
def stats(output, context, player, *args):
    attrs = player.attributes
    for acumenName in sorted(attrs.acumen):
        output.display("{name} acumen: {value}", name=acumenName,
                       value=attrs.acumen[acumenName])
        stats = attrs.stats[acumenName]
        for stat in sorted(stats):
            output.display(
                "\t{stat}: {value[0]:.2f} to {value[1]:.2f} multiplier",
                stat=stat, value=stats[stat])
        output.display("\n")


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
        context.remove(data.key)


functionRe = re.compile(
    r'(?P<function>[a-zA-Z0-9]+)\((?P<arguments>[\S ]+)\)'
    )


def parseFunction(data):
    result = functionRe.match(data)
    if result:
        result = result.groupdict()
        function, arguments = result['function'], result['arguments']
        args = [ast.literal_eval(x.strip()) for x in arguments.split(',')]
        return function, args
    return ('', '')


@command('use')
def use(output, context, player, *item: find):
    '''Use an object.'''
    if not item or len(item) > 1:
        raise output.error("What did you want to use?")
    data, item = item[0]
    if not 'use' in item.attributes:
        raise output.error("You can't use that.")
    function, arguments = parseFunction(item.attributes['use'])
    if function == 'script':
        script = context.entityCache.lookup(arguments[0])
        try:
            script.execute('main', output, context, player)
        except:  # yes, everything
            output.error("It doesn't work.")
            if output.permissions.get('debug', False):
                output.error(traceback.format_exc())
    else:
        output.error("You have no idea how to use that.")


@command('go')
def go(output, context, player, *args):
    '''Go in the specified direction.'''
    direction = ' '.join(args)
    target = context.outputs.get(direction)
    if target:
        if target.area != context.area and target.area:
            output.display(target.area.description)
        context.attributes['time'] += datetime.timedelta(minutes=20)
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
                    output.display(target.area.description)
                context.attributes['time'] += datetime.timedelta(minutes=20)
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
        output.display(player.description)
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
            output.display(items[0][1].description)


@command('quit', 'test.exit')
def quit(output, context, player, *args):
    output.quit()


@command('save')
def save(output, context, player, *args):
    data = player.save()
    output.display(player.location)
    player.entityCache.save('player', data, immediately=True)
    instances = collections.defaultdict(dict)
    for kind in player.entityCache['instances']:
        ds = player.entityCache['instances'][kind]
        for key in ds:
            entity = ds[key]
            proto = entity.prototype
            patch = archon.common.Merge(proto.attributes.save(),
                                        entity.attributes.save()).compared()
            if patch:
                output.display("Saving entity " + entity.location)
                instances[proto.location][entity.location] = patch
    instances = {
        "type": "metadata",
        "data": {
            "savegame_instances": instances
            }
        }

    stack = [context.entityCache.root]
    patches = {}
    while stack:
        ds = stack.pop()
        for key, thunk in ds.thunks.items():
            if isinstance(thunk, archon.objects.Room):
                _, originalData = ds.raw(key, format='.json')
                merge = archon.common.Merge(originalData, thunk.save())
                if merge.compared():
                    output.display("Saving room " + thunk.location)
                    patches[thunk.location] = merge.compared()
            elif isinstance(thunk, ds.__class__):
                stack.append(thunk)
    patches = {
        "type": "metadata",
        "data": {
            "savegame": patches
            }
        }
    player.entityCache.save("patches", patches, immediately=True)
    gameVars = {
        "type": "data",
        "data": {
            "lastRoom": context.location
            }
        }
    player.entityCache.save("gameVars", gameVars, immediately=True)
    output.display(
        "Save game created: {} objects saved".format(len(patches) + 1))


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
