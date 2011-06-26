import random
import collections

import archon.objects


class EnemyEntityHook(archon.objects.PlayerEntityHook):
    KIND = 'enemy'

    def __init__(self, entity, attributes):
        super().__init__(entity, attributes)
        self.attributes['friendlyName'] = attributes['character']['name']


class WeaponEntityHook(archon.objects.EntityHook):
    KIND = 'weapon'

    @property
    def effect(self):
        return self.attributes['effect']


class Effect(collections.namedtuple(
        'Effect',
        'hit target magnitude turns drain')):
    def hits(self):
        # needed if a long-lasting effect may not always hit
        if isinstance(self.hit, collections.Callable):  # Python 3.1 issue
            return self.hit()
        return self.hit

    @classmethod
    def healing(cls, target, magnitude, turns, drain):
        return cls(True, target, -magnitude, turns, drain)


EffectTarget = collections.namedtuple('EffectTarget',
                                      'category kind target')


class EffectEntityHook(archon.objects.EntityHook):
    KIND = 'effect'

    def message(self, name, **kwargs):
        return self.attributes['message'][name].format(**kwargs)

    def calculate(self, acumen, stats):
        return Effect(
            self.hits(stats['success']),
            self.target,
            self.magnitude(acumen),
            self.turns,
            self.drain(stats['drain'])
            )

    def hits(self, multiplier):
        multiplier = random.uniform(*multiplier)
        return random.random() <= (multiplier * self.stats['success'])

    def magnitude(self, acumen):
        return random.randint(*self.stats['magnitude']) * (acumen / 20)

    def drain(self, multiplier):
        multiplier = random.uniform(*multiplier)
        return multiplier * self.stats['drain']

    def fatigue(self, multiplier):
        multiplier = random.uniform(*multiplier)
        return Effect(
            True,
            'vitals:fatigue',
            multiplier * self.stats['fatigue'][0],
            self.stats['fatigue'][1],
            0
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
        target = self.stats['target'].split(':')
        if len(target) == 2:  # category-target with no kind
            return EffectTarget(target[0], None, target[1])
        elif len(target) == 3:  # category-kind-target
            return EffectTarget(*target)
        else:
            raise ValueError(
                "Improperly formatted effect target {}".format(target))

    @property
    def turns(self):
        # default not in data - templating requires always specifying this
        return self.stats.get('turns', 1)
