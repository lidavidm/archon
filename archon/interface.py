import sys
import collections
import archon.commands
import archon.common


class RestartError(Exception): pass


class CommandExecutionError(Exception):
    def __init__(self, message):
        self.message = message


class Interface(object):
    """
    Defines a player's interface to the game.

    Ideally there should be default implementations so that only display,
    restart, and prompt need be implemented (and perhaps repl).
    """
    def __init__(self,
                 permissions={'debug': False},
                 messageTemplates=None,
                 questionYes=('y', 'yes'),
                 questionNo=('n', 'no'),
                 replPrompt='{data}> '):
        self.questionYes = questionYes
        self.questionNo = questionNo
        self.permissions = permissions
        self.messageTemplates = messageTemplates
        self._replPrompt = replPrompt
        self.promptData = collections.OrderedDict()

    def prompt(self, prompt):
        pass

    def question(self, question, annotate=True):
        if annotate:
            separator = ' ' if question.endswith(' ') else ''
            question = separator.join([
                    question,
                    '[' + (', '.join(self.questionYes)) + ']',
                    '[' + (', '.join(self.questionNo)) + ']',
                    ''
                    ])
        res = self.prompt(question).strip().lower()
        if self.questionYes and res in self.questionYes:
            return True
        elif self.questionNo and res in self.questionNo:
            return False
        elif self.questionYes and self.questionNo:
            return self.question(question, annotate=False)
        else:
            # If there is no yes-answer list, and the result is not in the
            # no-answer list, then this returns False (anything not negative
            # is True); similar for no no-answer list
            return bool(self.questionYes)

    def display(self, text, *kwargs):
        pass

    def error(self, error):
        self.display(error)
        return CommandExecutionError(error)

    def restart(self, message=''):
        if message:
            self.display(message)
        raise RestartError

    def quit(self, message=''):
        if message:
            self.display(message)
        sys.exit()

    def menu(self, format, prompt, error, *choices, **keyChoices):
        while True:
            for index, choice in enumerate(choices):
                self.display(format.format(key=index, description=choice))
            for index, choice in sorted(keyChoices.items()):
                self.display(format.format(key=index, description=choice))
            choice = self.prompt(prompt).strip()
            if (choices and choice.isnumeric() and
                0 <= int(choice) <= len(choices)):
                return int(choice)
            elif choice in choices:
                return list(choices).index(choice)
            elif choice in keyChoices:
                return choice
            else:
                self.error(error)

    def repl(self, commands):
        pass

    @property
    def replPrompt(self):
        data = ' '.join([''.join(['{', name, '}'])
                         for name in self.promptData.keys()])
        prompt = self._replPrompt.format(data=data)
        return prompt.format(**self.promptData)


class ConsoleInterface(Interface):
    def prompt(self, prompt):
        return input(prompt)

    def display(self, text, **kwargs):
        if kwargs:
            text = text.format(**kwargs)
        print(text)

    def repl(self, context, player, commands):
        lastCommand = ''
        while True:
            try:
                self.promptData['time'] = context.attributes.timeString
                cmd = self.prompt(self.replPrompt).split()
                if cmd:
                    lastCommand = cmd[0]
                    cmd, args = commands.get(cmd[0]), cmd[1:]
                    context = cmd(self, context, player, *args)
            except RestartError:
                return
            except CommandExecutionError as e:
                pass
            except archon.common.DenotedNotFoundError:
                self.error('That is not a valid command.')
                close = commands.nearest(lastCommand)
                if close:
                    self.display('Did you mean:')
                    self.display('\n'.join(close))
