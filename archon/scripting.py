import archon.common
import archon.commands


def handles(signal):
    def _handles(func):
        archon.common.signal(signal).connect(func)
        return func


class Script:
    baseNamespace = {
        'handles': handles,
        'command': archon.commands.command
        }

    def __init__(self, script):
        self._script = script
        self._namespace = Script.baseNamespace
        exec(script, self._namespace)

    def execute(self, name, *args, **kwargs):
        return self.get(name)(*args, **kwargs)

    def get(self, name):
        return self._namespace[name]
