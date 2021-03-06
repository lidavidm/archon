import random
import collections

import archon.objects


class EnemyEntityHook(archon.objects.PlayerEntityHook):
    KIND = 'enemy'

    @property
    def friendlyName(self):
        return self.attributes['character']['name']

    @property
    def description(self):
        return self.attributes['character']['description']


class WeaponEntityHook(archon.objects.EntityHook):
    KIND = 'weapon'

    @property
    def effect(self):
        return self.attributes['effect']


class EffectMissed(Exception): pass


class NotEnoughAP(Exception): pass


class Effect:
    def __init__(self, hit, target, magnitude, turns, drain, messages):
        self.hit = hit
        self.target = target
        self.magnitude = magnitude
        self.turns = turns
        self.drain = drain
        self.messages = messages

    def message(self, name):
        message = self.messages.messages[name]
        return message.format(effect=self, **self.messages.objects)

    def apply(self, user, target):
        if self.drain <= user.attributes.vitals['ap']:
            user.attributes.damage(self.drain, 'vital', None, 'ap')
            if self.hit:
                return target.attributes.damage(
                    self.magnitude, **self.target._asdict())
            else:
                raise EffectMissed
        else:
            raise NotEnoughAP

    def modify(self, other):
        """
        Creates a new effect using this effect to modify the other.

        Messages and the :attr:`hit` flag are not affected.
        """
        return Effect(
            other.hit,
            self.target,
            self.magnitude + other.magnitude,
            self.turns + other.turns,
            self.drain + other.drain,
            other.messages)

    def __repr__(self):
        a = "<Effect {hit} {target} {magnitude} {turns} {drain} {messages}>"
        return a.format(**self.__dict__)


class EffectTarget(collections.namedtuple('EffectTarget',
                                      'category kind target')):
    @classmethod
    def viaString(cls, target):
        target = target.split(':')
        if len(target) == 2:  # category-target with no kind
            return EffectTarget(target[0], None, target[1])
        elif len(target) == 3:  # category-kind-target
            return EffectTarget(*target)
        else:
            raise ValueError(
                "Improperly formatted effect target {}".format(target))

EffectMessage = collections.namedtuple('EffectMessage',
                                       'messages objects')


class EffectEntityHook(archon.objects.EntityHook):
    KIND = 'effect'

    @classmethod
    def healingT(cls, magnitude, turns, targetAttr=None, **kwargs):
        """
        Create a default healing effect from the "heal" template.
        """
        template = cls.templates['heal']
        targetAttr = (EffectTarget.viaString(targetAttr) or
                      template.attributes.target)
        return Effect(
            True, targetAttr, -magnitude, turns, 0,
            EffectMessage(template.attributes['message'], kwargs))

    @classmethod
    def fatigueT(cls, magnitude, turns, **kwargs):
        template = cls.templates['fatigue']
        return Effect(
            True, template.attributes.target, magnitude, turns, 0,
            EffectMessage(template.attributes['message'], kwargs))

    def instance(self, acumen, stats, **kwargs):
        return Effect(
            self.hits(stats['success']),
            self.target,
            self.magnitude(acumen),
            self.turns,
            self.drain(stats['drain']),
            EffectMessage(self.attributes['message'], kwargs)
            )

    def hits(self, multiplier):
        multiplier = random.uniform(*multiplier)
        return random.random() <= (multiplier * self.stats['success'])

    def magnitude(self, acumen):
        return random.randint(*self.stats['magnitude']) * (acumen / 20)

    def drain(self, multiplier):
        multiplier = random.uniform(*multiplier)
        return multiplier * self.stats['drain']

    def fatigue(self, multiplier, **kwargs):
        multiplier = random.uniform(*multiplier)
        return EffectEntityHook.fatigueT(
            multiplier * self.stats['fatigue'][0],
            self.stats['fatigue'][1],
            **kwargs
            )

    @property
    def effectKind(self):
        for kind in ('damage', 'heal'):
            if kind in self.attributes:
                return kind

    @property
    def stats(self):
        return self.attributes[self.effectKind]

    @property
    def target(self):
        return EffectTarget.viaString(self.stats['target'])

    def turns(self):
        # default not in data - templating requires always specifying this
        return self.stats.get('turns', 1)


ChatTopic = collections.namedtuple('ChatTopic', 'contents actions')


class Conversation:
    def __init__(self, npc, cache, *dialouge):
        self.npc = npc
        self.cache = cache
        self.dialouges = [self.cache.lookup(d).attributes for d in dialouge]
        topics = {}
        self._hidden = {}
        for dialouge in self.dialouges:
            topics.update(dialouge['visible'])
            self._hidden.update(dialouge['invisible'])
        self.topicIndex = list(topics.items())
        self.topicIndex.append(("bye", None))
        self.actions = {'visible': self.visible, 'script': self.script}

    def isEnd(self, choice):
        return choice == len(self.topicIndex) - 1

    def removeTopic(self, topic):
        for index, (t, _) in enumerate(self.topicIndex):
            if t == topic:
                del self.topicIndex[index]
                return

    def visible(self, output, context, player, *topics):
        self.topicIndex.pop()  # remove "bye"
        topics = (
            t for t in topics if t in self._hidden and
            t not in self.topicIndex)
        for topic in topics:
            self.topicIndex.append((topic, self._hidden[topic]))
            del self._hidden[topic]
        self.topicIndex.append(("bye", None))

    def script(self, output, context, player, script, *args):
        s = self.cache.lookup(script)
        s.execute('main', output, context, player, self.npc, self, *args)

    @property
    def topics(self):
        return (t[0] for t in self.topicIndex)


class NPCEntityHook(archon.objects.MutableEntityHook):
    KIND = 'npc'

    def __init__(self, entity, attributes):
        super().__init__(entity, attributes)
        self.conversation = Conversation(self.entity,
                                         self.entity.entityCache,
                                         *self.attributes['dialouge'])
