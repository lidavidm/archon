class Entity(object):
    def __init__(self, datastore):
        pass


class Room(object):
    def __init__(self, datastore):
        pass

    def find(self):
        pass

    def add(self):
        pass

    def remove(self):
        pass

    def describe(self):
        pass

    @property
    def outputs(self):
        pass

    @property
    def inputs(self):
        pass


class Command(object):
    def run(self, context, player, output, *args):
        pass


class Interface(object):
    def prompt(self, prompt):
        pass

    def question(self, question):
        pass

    def display(self, text):
        pass
