import difflib
import archon.commands


class RestartError(Exception):pass


class Entity(object):
    def __init__(self, kind):
        self._kind = kind
        self._capabilities = {}
        self._attributes = {}

    def when(self, name, actions):
        self._capabilities[name] = actions

    def do(self, name, output, context=None, player=None):
        dependencies = [output]
        if context:
            dependencies.append(context)
        if player:
            dependencies.append(player)
        for f, args in self.capabilities[name]:
            f(*(dependencies + args))

    @property
    def capabilities(self):
        return self._capabilities

    @property
    def attributes(self):
        return self._attributes

    @attributes.setter
    def attributes(self, value):
        self._attributes = value


class Room(Entity):
    ROOM_ENTITY_KIND = object()

    def __init__(self, kind, description):
        super(Room, self).__init__(kind)
        self._description = description
        self._entityCache = None
        self._contents = {}
        self._outputs = {}

    def naturalFind(self, text):
        """
        Attempt to find an entity key based on a variety of criteria.

        Returns None if there is no match.

        If there is no unique entity matched, return a set of all possible
        matches. Else, return the only match.
        """
        # identity, prefix-identity, or key, with key taking precedence
        matches = set()
        if text in self.contents:  # it's a key
            matches.add(text)

        crit = text.split()

        for key, entity in self.contents.iteritems():
            if entity[1] == crit[-1]:
                matches.add(key)
        if matches:
            if len(matches) == 1:
                return matches[0]
            elif len(crit) > 1:  # there's a prefix
                prefix = text[:-crit[-1]].rstrip()  # get the prefix
                for key, entity in self.contents.iteritems():
                    if entity[4] == prefix:
                        return key  # prefix-identity should be unique
            else:
                return matches
        return None

    def add(self, entityKind, key, identity,
            location='', description='', prefix='', target=''):
        if entityKind is self.ROOM_ENTITY_KIND:
            self._outputs[key] = (target, identity,
                                  location, description, prefix)
        else:
            self._contents[key] = (entityKind, identity,
                                   location, description, prefix)

    def remove(self, key):
        del self._contents[key]

    def describe(self, key=None):
        """
        Describe the specified object, or if not given, the room.
        """
        if key:
            entity = self.allContents[key]
            beginning = ''
            if key in self.contents:
                beginning = 'There is'
            elif key in self.outputs:
                beginning = 'You can go'
                if entity[4]:  # if there's a prefix, add "to"
                    beginning += ' to'
            text = '{beginning} {prefix}{identity}{location}.'.format(
                beginning=beginning,
                prefix=entity[4] + ' ' if entity[4] else '',
                identity=entity[1],
                location=' ' + entity[2] if entity[2] else ''
                ).strip()
            if entity[3]:
                text = ' '.join([text, 'It is', entity[3] + '.'])
            return text
        else:
            return '\n'.join(
                ['You are in ' + self._description] +
                [self.describe(key) for key in self.contents] +
                [self.describe(key) for key in self.outputs])

    def enter(self):
        pass

    def exit(self):
        pass

    @property
    def entityCache(self):
        return self._entityCache

    @entityCache.setter
    def entityCache(self, cache):
        self._entityCache = cache

    @property
    def contents(self):
        return self._contents

    @property
    def outputs(self):
        return self._outputs

    @property
    def allContents(self):
        return dict(self._contents.viewitems() | self._outputs.viewitems())

    @property
    def inputs(self):
        pass


class Interface(object):
    def __init__(self, questionYes=('y', 'yes'), questionNo=None):
        self.questionYes = questionYes
        self.questionNo = questionNo

    def prompt(self, prompt):
        pass

    def question(self, question):
        pass

    def display(self, text):
        pass

    def error(self, error):
        pass

    def restart(self, message=''):
        pass

    def repl(self, commands):
        pass


class ConsoleInterface(Interface):
    def prompt(self, prompt):
        return raw_input(prompt)

    def question(self, question):
        res = raw_input(question).strip().lower()
        if self.questionYes and res in self.questionYes:
            return True
        elif self.questionNo and res in self.questionNo:
            return False
        else:
            # If there is no yes-answer list, and the result is not in the
            # no-answer list, then this returns False (anything not negative
            # is True)
            # If there is no no-answer list, and the result is not in the
            # yes-answer list, then this returns True (anything not
            # affirmative is False)
            return bool(self.questionYes)

    def display(self, text):
        print text

    error = display

    def restart(self, message=''):
        if message:
            self.display(message)
        raise RestartError

    def repl(self, context, player, commands):
        lastCommand = ''
        while True:
            try:
                cmd = self.prompt('> ').split()
                lastCommand = cmd[0]
                cmd, args = commands.get(cmd[0]), cmd[1:]
                context = cmd(self, context, player, *args)
            except (KeyboardInterrupt, RestartError):
                return
            except archon.commands.CommandNotFoundError:
                self.error('That is not a valid command.')
                close = difflib.get_close_matches(
                    lastCommand,
                    commands.commands.keys()
                    )
                if close:
                    self.display('Did you mean:')
                    self.display('\n'.join(close))
