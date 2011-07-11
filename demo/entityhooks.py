import random
import collections

import archon.objects


class EnemyEntityHook(archon.objects.PlayerEntityHook):
    KIND = 'enemy'

    def __init__(self, entity, attributes):
        super().__init__(entity, attributes)

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
