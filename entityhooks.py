import random

import archon.objects


class EnemyEntityHook(archon.objects.PlayerEntityHook):
    KIND = 'enemy'


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
        return round(random.randint(*self.stats['damage']) * multiplier)

    def apUse(self, multiplier):
        multiplier = random.uniform(*multiplier)
        return round(multiplier * self.stats['drain'])

    def fatigue(self, multiplier):
        multiplier = random.uniform(*multiplier)
        return (round(multiplier * self.stats['fatigue'][0]),
                self.stats['fatigue'][1])
