import sys
import archon.commands
import archon.common


class RestartError(Exception): pass


class Interface(object):
    """
    Defines a player's interface to the game.

    Ideally there should be default implementations so that only display,
    restart, and prompt need be implemented (and perhaps repl).
    """
    def __init__(self, questionYes=('y', 'yes'), questionNo=None):
        self.questionYes = questionYes
        self.questionNo = questionNo

    def prompt(self, prompt):
        pass

    def question(self, question):
        # TODO display input choices to player
        res = self.prompt(question).strip().lower()
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
        pass

    def error(self, error):
        pass

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

    error = display

    def repl(self, context, player, commands):
        lastCommand = ''
        while True:
            try:
                cmd = self.prompt('> ').split()
                lastCommand = cmd[0] if cmd else lastCommand
                cmd, args = commands.get(cmd[0]), cmd[1:]
                context = cmd(self, context, player, *args)
            except (KeyboardInterrupt, RestartError):
                return
            except archon.common.DenotedNotFoundError:
                self.error('That is not a valid command.')
                close = commands.nearest(lastCommand)
                if close:
                    self.display('Did you mean:')
                    self.display('\n'.join(close))
