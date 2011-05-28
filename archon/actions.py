NORMAL = 'normal'  # take only output
REFLEXIVE = 'reflexive'  # instead of taking player, take entity
CONTEXTUAL = 'contextual'  # take the room
TRANSITIVE = 'transitive'  # transitive to the player (take the player)
# XXX how to do unions


class action(object):
    """
    Denote a function as an action.
    """
    actions = {}

    def __init__(self, name, kind=NORMAL):
        if name in self.__class__.actions:
            raise ValueError("Action name {} already in use!".format(name))
        self.name = name
        self.kind = kind

    def __call__(self, func):
        self.originalFunction = func
        self.__class__.actions[self.name] = self.activate
        # mirror the original name
        # XXX mirror the action name?
        self.activate.im_func.func_name = func.func_name
        return self.activate

    def activate(self, *args):
        return self.originalFunction(*args)

    @classmethod
    def get(cls, name):
        return cls.actions[name]

    @classmethod
    def normal(cls, name):
        return cls(name, kind=NORMAL)

    @classmethod
    def reflexive(cls, name):
        return cls(name, kind=REFLEXIVE)

    @classmethod
    def contextual(cls, name):
        return cls(name, kind=CONTEXTUAL)

    @classmethod
    def transitive(cls, name):
        return cls(name, kind=TRANSITIVE)

getAction = action.get


@action.normal('test')
def testAction(output, *args):
    print args


@action.normal('ui.notify')
def notify(output, message):
    print message
