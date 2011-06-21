#!/usr/bin/env python3
import collections

import archon
import archon.objects
import archon.commands
import archon.common
import archon.interface


class battlecommand(archon.commands.command):
    pass


class Effect(collections.namedtuple('Effect', 'turns target amount')):
    @classmethod
    def healing(cls):
        pass
# target should be a callable or property


enemy = archon.commands.find
# TODO: also lookup by index (for duplicate enemies)


def ProxyInterface(parent):
    class ProxyInterface(parent):
        def repl(self, context, player, commands):
            lastCommand = ''
            while True:
                try:
                    vitals = player.attributes.vitals
                    self.promptData.update(
                        turn='Turn {}'.format(context.attributes['turn']),
                        hp='HP {:.1g}'.format(vitals['health']),
                        ap='AP {:.1g}'.format(vitals['ap'])
                        )
                    cmd = self.prompt(self.replPrompt).split()
                    lastCommand = cmd[0] if cmd else lastCommand
                    cmd, args = commands.get(cmd[0]), cmd[1:]
                    context = cmd(self, context, player, *args)
                except archon.interface.RestartError:
                    return
                except archon.interface.CommandExecutionError as e:
                    pass
                except archon.common.DenotedNotFoundError:
                    self.error('That is not a valid command.')
                    close = commands.nearest(lastCommand)
                    if close:
                        self.display('Did you mean:')
                        self.display('\n'.join(close))
    return ProxyInterface


def _healPlayerAP(player):
    def _healAP(amount):
        player.vitals['ap'] += amount
        if player.vitals['ap'] > player.maxVitals['ap']:
            player.vitals['ap'] = player.maxVitals['ap']
    return _healAP


# XXX some way of hiding this from the player
@battlecommand('applyBattleEffects')
def applyBattleEffects(output, context, player):
    for effect in battlecommand('battle').data['effects'][player]:
        pass  # apply fatigue, continuous damage, etc.


@battlecommand('playerTurn')
def playerTurn(output, context, player, *args):
    context.attributes['turn'] += 1
    for key in context.contents:
        entity = context.entityFor(key)
        if entity.kind == 'enemy':
            output.display('{}: {:.1g} HP'.format(
                    entity.friendlyName,
                    entity.attributes.vitals['health']
                    ))
    battlecommand.get('applyBattleEffects')(output, context, player)


@battlecommand('enemyTurn')
def enemyTurn(output, context, player, *args):
    battlecommand.get('applyBattleEffects')(output, context, player)
    output.display("The enemy does nothing.")
    battlecommand.get('playerTurn')(output, context, player)


@archon.commands.command('fight')
def fight(output, context, player, *enemy: archon.commands.find):
    # TODO doesn't check if enemy found was ambiguous
    if not enemy or enemy[0][1].kind != 'enemy':
        raise output.error("You can't fight that.")
    battlecommand('battle').data = {'effects': {
            player: [
                Effect(-1, _healPlayerAP(player),
                        player.attributes.maxVitals['ap'] / 10)
                ]
            }}
    data, enemy = enemy[0]
    scene = context.entityCache.lookup(
        context.area.attributes['battleScene']
        )
    scene.attributes['turn'] = 0
    scene.entityCache = context.entityCache
    scene.add(data.objectLocation, data.key, data.location,
              data.description, data.prefix, data.options)
    # XXX problem: entity object is recreated each time - how to preserve
    # enemy data through turns?
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
        if slot in player.attributes.equip and player.attributes.equip[slot]:
            weapons.append(player.attributes.equip[slot])
    if not weapons:
        raise output.error("You need a weapon equipped to attack!")
    stats = player.attributes.stats['physical']
    physicalAcumen = player.attributes.acumen['physical']
    for weapon in weapons:
        apCost = weapon.attributes.apUse(multiplier=stats['drain'])
        player.attributes.damage(apCost, None, 'ap')
        if weapon.attributes.hits(multiplier=stats['success']):
            damage = weapon.attributes.damage(multiplier=physicalAcumen)
            fatigue, fatigueTurns = weapon.attributes.fatigue(
                multiplier=stats['fatigue'])
            if apCost <= player.attributes.vitals['ap']:
                realDamage = target.attributes.damage(damage, 'physical')
                output.display("You hit with {} for {}".format(
                        weapon.friendlyName,
                        realDamage
                        ))
            else:
                output.display("You don't have enough AP to attack.")
        else:
            output.display("You missed with {}".format(
                    weapon.friendlyName
                    ))
    battlecommand.get('enemyTurn')(output, context, player)
