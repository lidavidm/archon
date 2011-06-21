import random

import archon.objects


class EnemyEntityHook(archon.objects.PlayerEntityHook):
    KIND = 'enemy'

    def __init__(self, entity, attributes):
        super().__init__(entity, attributes)
        self.attributes['friendlyName'] = attributes['character']['name']


class WeaponEntityHook(archon.objects.EntityHook):
    KIND = 'weapon'

    @property
    def stats(self):
        return self.attributes['attack']

    def hits(self, multiplier):
        multiplier = random.uniform(*multiplier)
        return random.random() <= (multiplier * self.stats['success'])

    def damage(self, multiplier):
        multiplier /= 20
        return random.randint(*self.stats['damage']) * multiplier

    def apUse(self, multiplier):
        multiplier = random.uniform(*multiplier)
        return multiplier * self.stats['drain']

    def fatigue(self, multiplier):
        multiplier = random.uniform(*multiplier)
        return (multiplier * self.stats['fatigue'][0],
                self.stats['fatigue'][1])
