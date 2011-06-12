import sys
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
                 questionYes=('y', 'yes'),
                 questionNo=('n', 'no')):
        self.questionYes = questionYes
        self.questionNo = questionNo
        self.permissions = permissions

    def prompt(self, prompt):
        pass

    def question(self, question, annotate=True):
        # TODO display input choices to player
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

    def display(self, text):
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

    def menu(self, choiceFormat, prompt, **choices):
        # XXX needs use-cases so that features can be added/removed
        for option, description in sorted(
            iter(choices.items()),
            key=lambda x: x[0]):
            self.display(choiceFormat.format(option=option,
                                             description=description))
        while True:
            choice = self.prompt(prompt).strip()
            if choice in choices:
                return choice

    def repl(self, commands):
        pass


class ConsoleInterface(Interface):
    def prompt(self, prompt):
        return input(prompt)

    def display(self, text):
        print(text)

    def repl(self, context, player, commands):
        lastCommand = ''
        prompt = '{time}> '
        while True:
            try:
                promptString = prompt.format(
                    time=context.attributes['timeString']
                    )
                cmd = self.prompt(promptString).split()
                lastCommand = cmd[0] if cmd else lastCommand
                cmd, args = commands.get(cmd[0]), cmd[1:]
                context = cmd(self, context, player, *args)
            except (KeyboardInterrupt, RestartError):
                return
            except CommandExecutionError as e:
                pass
            except archon.common.DenotedNotFoundError:
                self.error('That is not a valid command.')
                close = commands.nearest(lastCommand)
                if close:
                    self.display('Did you mean:')
                    self.display('\n'.join(close))
