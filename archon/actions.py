

class action(object):
    """
    Denote a function as an action.
    """
    actions = {}

    def __init__(self, name):
        if name in self.__class__.actions:
            raise ValueError("Action name {} already in use!".format(name))
        self.name = name

    def __call__(self, func):
        self.__class__.actions[self.name] = func
        return func

    @classmethod
    def get(cls, name):
        return cls.actions[name]

getAction = action.get


@action('test')
def testAction(*args):
    print args


@action('ui.notify')
def notify(message):
    print message
