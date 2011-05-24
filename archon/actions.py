NORMAL = 'normal'
REFLEXIVE = 'reflexive'
CONTEXTUAL = 'contextual'
TRANSITIVE = 'transitive'  # transitive to the player


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
        self.__class__.actions[self.name] = func
        return func

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
