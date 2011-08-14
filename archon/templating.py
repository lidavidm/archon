import re
import ast

import archon.common
import archon.entity


class transform(archon.common.denoter):
    functions = {}


class predicate(archon.common.denoter):
    functions = {}


class TemplatingDict(dict):
    def __init__(self, dictionary, **kwargs):
        dictionary.update(kwargs)
        super().__init__(dictionary)
        self.kwargs = kwargs

    def __getattr__(self, key):
        if key.endswith('_capitalized'):
            return super().__getitem__(key[:-12]).capitalize()
        elif key in self:
            item = super().__getitem__(key)
            if isinstance(item, dict):
                return TemplatingDict(item, **self.kwargs)
            elif isinstance(item, str) and '{' in item and '}' in item:
                return item.format(**self)
            return item
        raise AttributeError(key)

    __getitem__ = __getattr__


class MessageTemplateEntityHook(archon.entity.EntityHook):
    KIND = "message_template"
    templates = {}
    fieldRe = re.compile(r"{(.*)@(.*)}")
    funcRe = re.compile(r"(.?[a-zA-Z0-9]*)(?:\((.*)\))?")

    def __init__(self, entity, attributes):
        super().__init__(entity, attributes)
        for key, template in attributes.items():
            MessageTemplateEntityHook.templates[key] = template

    @classmethod
    def format(cls, mode, text, *args, **kwargs):
        """
        Formatting syntax: {format_string[@new_syntax]}
        new syntax:
        name - calls a function
        name(" ", 2, 3) - calls a function with parameters
        name + name2 - composes functions (applied right-to-left)
        .upper - calls a string method

        The formatting directive is first applied before functions are
        called, then all are substituted into the original string.
        For non-method functions, signatures are as such:
        def function(text, *args, nextFunction=None):
        """
        replNumber = -1
        replFormats = {}  # value is 2-tuple (format, extension)

        def repl(match):
            nonlocal replNumber
            replNumber += 1
            replFormats[replNumber] = match.group(1, 2)
            return ''.join(['{__MTEH', str(replNumber), '}'])
        text = cls.fieldRe.sub(repl, text)
        formatKeys = cls.template(mode, **kwargs)
        for key, (original, extension) in replFormats.items():
            key = ''.join(['{__MTEH', str(key), '}'])
            original = ''.join(['{', original, '}'])
            subtext = original.format(*args, **formatKeys)
            subtext = cls.formatExtension(subtext, extension)
            text = text.replace(key, subtext)
        return text

    @classmethod
    def formatExtension(cls, text, fmt):
        """Processes the extended part of a format string.

        :param text: The expanded original part of the format string.
        :param fmt: The extended part of the format string."""
        for func in reversed(fmt.split('+')):
            func = func.strip()
            match = cls.funcRe.match(func)
            if not match:
                raise ValueError("Invalid expression " + func)
            func, args = match.groups()
            res = cls.evaluate(text, func, args)
            if res is True:
                continue
            elif res is False:
                return text
            else:
                text = res
        return text

    @classmethod
    def evaluate(cls, text, func, args):
        if func.startswith('!'):
            return not cls.evaluate(text, func[1:], args)
        elif func.startswith('.'):
            return getattr(text, func[1:])()
        else:
            if args:
                args = map(ast.literal_eval, args.split(','))
            else:
                args = []
            if predicate.contains(func):
                return predicate.get(func)(text, *args)
            elif transform.contains(func):
                return transform.get(func)(text, *args)
            else:
                raise ValueError(
                    "Format function {} not found".format(func))

    @classmethod
    def template(cls, key, **kwargs):
        item = cls.templates[key]
        if isinstance(item, dict):
            return TemplatingDict(item, **kwargs)
        return item


class MessagesEntityHook(archon.entity.EntityHook):
    KIND = "messages"

    def message(self, name, *args, **kwargs):
        return MessageTemplateEntityHook.format(
            self.attributes['mode'],
            self.attributes['messages'][name],
            *args, **kwargs)


@predicate('empty')
def empty(text):
    return not text


@transform('prepend')
def prepend(text, char):
    return char + text
