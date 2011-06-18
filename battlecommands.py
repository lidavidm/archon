#!/usr/bin/env python3
import collections

import archon
import archon.objects
import archon.commands
import archon.common
import archon.interface


class battlecommand(archon.commands.command):
    pass


Effect = collections.namedtuple('Effect', 'turns target amount')
# target should be a callable or property


enemy = archon.commands.find


def ProxyInterface(parent):
    class ProxyInterface(parent):
        pass
    return ProxyInterface


def _healPlayerAP(player):
    def _heal(amount):
        player.vitals['ap'] += amount
        if player.vitals['ap'] > player.maxVitals['ap']:
            player.vitals['ap'] = player.maxVitals['ap']
    return _heal


# XXX some way of hiding this from the player
@battlecommand('applyBattleEffects')
def applyBattleEffects(output, context, player):
    for effect in battlecommand('battle').data['effects'][player]:
        pass  # apply fatigue, continuous damage, etc.


@battlecommand('playerTurn')
def playerTurn(output, context, player, *args):
    battlecommand.get('applyBattleEffects')(output, context, player)


@battlecommand('enemyTurn')
def enemyTurn(output, context, player, *args):
    battlecommand.get('applyBattleEffects')(output, context, player)
    battlecommand.get('playerTurn')(output, context, player)


@archon.commands.command('fight')
def fight(output, context, player, *enemy: archon.commands.find):
    if not enemy or enemy[0][1].kind != 'enemy':
        raise output.error("You can't fight that.")
    battlecommand('battle').data = {'effects': {
            Effect(-1, _healPlayerAP(player),
                    player.attributes.maxVitals['ap'] / 10)
            }}
    data, enemy = enemy[0]
    scene = context.entityCache.lookup(
        context.area.attributes['battleScene']
        )
    scene.entityCache = context.entityCache
    scene.add(data.objectLocation, 0, data.identity, data.location,
              data.description, data.prefix, data.options)
    # TODO find way of generating key for multiple-enemy battles
    battleOutput = ProxyInterface(output.__class__)()
    battleOutput.repl(scene, player, battlecommand)
    output.display('Battle ended.')


@battlecommand('attack')
def attack(output, context, player, *target: enemy):
    if len(target) > 1 or not target:
        raise output.error("You can attack exactly one enemy at a time.")
    data, target = target[0]
    weapons = []
    for slot in ('left hand', 'right hand'):
        if slot in player.attributes.equip:
            weapons.append(player.attributes.equip[slot])
    if not weapons:
        raise output.error("You need a weapon equipped to fight!")
    stats = player.attributes.stats['physical']
    physicalAcumen = player.attributes.acumen['physical']
    for weapon in weapons:
        if weapon.hits(multiplier=stats['success']):
            damage = weapon.damage(multiplier=physicalAcumen)
            apCost = weapon.apUse(multiplier=stats['drain'])
            fatigue, fatigueTurns = weapon.fatigue(
                multiplier=stats['fatigue'])
            # enemy absorb
    battlecommand.get('enemyTurn')(output, context, player)
