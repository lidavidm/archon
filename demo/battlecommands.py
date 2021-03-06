#!/usr/bin/env python3
import random
import collections

import archon
import archon.objects
import archon.commands
import archon.common
import archon.interface

import entityhooks


class BattleEnded(Exception): pass


class battlecommand(archon.commands.command):
    functions = {}
    preExecute = archon.common.signal('battlecommand.preExecute')
    postExecute = archon.common.signal('battlecommand.postExecute')


class Battle:
    def __init__(self, output, scene, player, enemies):
        self.output = output
        self.scene = scene
        self.player = player
        self.enemies = enemies
        self.effects = collections.defaultdict(list)
        self.effects[player] = [
            entityhooks.EffectEntityHook.healingT(
                player.attributes.vitals['ap'] / 30, -1,
                'vital:ap', target=player
                )]

    def applyEffects(self, target, targetT):
        for effect in self.effects.get(target, []):
            if effect.hit:
                target.attributes.damage(effect.magnitude,
                                         **effect.target._asdict())
                self.output.display(effect.message('success'))
            effect.turns -= 1
            if effect.turns == 0:  # negative value -> infinite turns
                self.effects[target].remove(effect)

    def playerTurn(self):
        self.scene.attributes['turn'] += 1
        for enemy in self.enemies:
            self.output.display('{}: {:.1f} HP'.format(
                    enemy.friendlyName,
                    enemy.attributes.vitals['health']
                    ))
        vitals = self.player.attributes.vitals
        self.output.promptData.update(
            turn='Turn {}'.format(self.scene.attributes['turn']),
            hp='HP: {:.1f}'.format(vitals['health']),
            ap='AP: {:.1f}'.format(vitals['ap'])
            )
        self.applyEffects(self.player, 'second_person')

    def enemyTurn(self):
        for enemy in self.enemies:
            self.applyEffects(enemy, 'third_person')
            if enemy.attributes.vitals['health'] <= 0:
                self.enemies.remove(enemy)
                self.output.display(enemy.friendlyName + ' died.')
            args = archon.commands.parseFunction(
                enemy.attributes.character['ai'])[1]
            script = enemy.entityCache.lookup(args[0])
            script.execute(args[1],
                           self.output,
                           self.scene,
                           performAttacks,
                           enemy,
                           self.player)
        if not self.enemies:
            self.output.display("You win!")
            raise BattleEnded

    def run(self):
        olddata = self.output.promptData.copy()
        self.output.promptData.clear()
        # postExecute is not run in case of error
        battlecommand.postExecute.connect(
            lambda cmd, **args: (self.enemyTurn(), self.playerTurn()),
            weak=False)
        if random.random() > 0.5: self.enemyTurn()  # surprised!
        try:
            self.output.repl(self.scene, self.player, battlecommand)
        except BattleEnded:
            self.output.promptData.clear()
            self.output.promptData.update(olddata)
            self.scene.clearContents()


enemy = archon.commands.find
# TODO: also lookup by index (for duplicate enemies)


@archon.commands.command('fight')
def fight(output, context, player, *enemies: archon.commands.findMulti):
    if not enemies:
        raise output.error("You need to fight something.")
    scene = context.entityCache.lookup(
        context.area.attributes['battleScene']
        )
    # TODO fallback for no area
    scene.attributes['turn'] = 0
    scene.entityCache = context.entityCache
    enemyList = []
    for data, enemy in enemies:
        if enemy.kind != 'enemy':
            raise output.error("You can't fight that.")
        enemy.attributes.vitals.update(enemy.attributes.maxVitals)
        enemyList.append(enemy)
        scene.add(data.objectLocation, data.key, data.location,
                  data.description, data.prefix, data.options, enemy)
    battle = Battle(output, scene, player, enemyList)
    battlecommand('battle').data = battle
    battle.run()
    for data, enemy in enemies:
        context.remove(data.key)
    output.display('Battle ended.')


@battlecommand('wait', 'skip')
def wait(output, context, player):
    output.display("You do nothing.")


@battlecommand('attack')
def attack(output, context, player, *target: enemy):
    if len(target) > 1 or not target:
        raise output.error("You can attack exactly one enemy at a time.")
    data, target = target[0]
    weapons = []
    for slot in ('left hand', 'right hand'):
        if slot in player.attributes.equip and player.attributes.equip[slot]:
            weapons.append(player.attributes.equip[slot])
    if not weapons:
        raise output.error("You need a weapon equipped to attack!")
    stats = player.attributes.stats['physical']
    physicalAcumen = player.attributes.acumen['physical']
    performAttacks(output, context, player, target, 'physical', *weapons)


def performAttacks(output, context, user, target, acumenType, *weapons):
    stats = user.attributes.stats[acumenType]
    acumen = user.attributes.acumen[acumenType]
    for weapon in weapons:
        wEffect = weapon.attributes.effect.attributes
        effect = wEffect.instance(acumen, stats, user=user, target=target)
        for item in target.attributes.equip.values():
            if item and item.kind == 'armor':
                item.attributes.modifier.modify(effect)
        try:
            realDamage = effect.apply(user, target)
            battlecommand('battle').data.effects[user].append(
                wEffect.fatigue(stats['fatigue'], target=user))
            output.display(effect.message('success'))
        except entityhooks.EffectMissed:
            output.display(effect.message('failure'))
        except entityhooks.NotEnoughAP:
            output.display(effect.message('insufficient_ap'))
