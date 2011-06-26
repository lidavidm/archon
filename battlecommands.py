#!/usr/bin/env python3
import collections

import archon
import archon.objects
import archon.commands
import archon.common
import archon.interface

import entityhooks


class battlecommand(archon.commands.command):
    pass


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
                        hp='HP {:.1f}'.format(vitals['health']),
                        ap='AP {:.1f}'.format(vitals['ap'])
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


# XXX some way of hiding this from the player
@battlecommand('applyBattleEffects')
def applyBattleEffects(output, context, player):
    effects = battlecommand('battle').data['effects']
    for target in effects:
        for effect in effects[target]:
            if effect.hits():
                target.attributes.damage(effect.magnitude,
                                         **effect.target._asdict())
                output.display(str(effect))
            if effect.turns == 0:  # negative value -> infinite turns
                effects[target].remove(effect)


@battlecommand('playerTurn')
def playerTurn(output, context, player, *args):
    context.attributes['turn'] += 1
    for key in context.contents:
        entity = context.entityFor(key)
        if entity.kind == 'enemy':
            output.display('{}: {:.1f} HP'.format(
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
def fight(output, context, player, *enemies: archon.commands.findMulti):
    if not enemies:
        raise output.error("You need to fight something.")
    scene = context.entityCache.lookup(
        context.area.attributes['battleScene']
        )
    scene.attributes['turn'] = 0
    scene.entityCache = context.entityCache
    for data, enemy in enemies:
        if enemy.kind != 'enemy':
            raise output.error("You can't fight that.")
        scene.add(data.objectLocation, data.key, data.location,
                  data.description, data.prefix, data.options)
    battlecommand('battle').data = {
        'effects': {
            player: [entityhooks.Effect.healing(
                    entityhooks.EffectTarget('vital', None, 'ap'),
                    player.attributes.maxVitals['ap'] / 30, -1, 0
                    )]
            },
        'enemies': [x[1] for x in enemies]  # get only the entities
        }
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
        weaponEffect = weapon.attributes.effect.attributes
        effect = weaponEffect.calculate(physicalAcumen, stats)
        try:
            realDamage = applyEffect(player, target, effect)
            output.display(weaponEffect.message(
                    'success',
                    user='You', target='the enemy',
                    magnitude=realDamage, item=weapon.friendlyName))
        except EffectMissed:
            output.display(weaponEffect.message('failure', user='You'))
        except NotEnoughAP:
            output.display("You don't have enough AP to attack.")

    battlecommand.get('enemyTurn')(output, context, player)


def applyEffect(user, target, effect):
    if effect.drain <= user.attributes.vitals['ap']:
        user.attributes.damage(effect.drain, 'vital', None, 'ap')
        if effect.hits():
            return target.attributes.damage(
                effect.magnitude, **effect.target._asdict())
        else:
            raise EffectMissed
    else:
        raise NotEnoughAP


class EffectMissed(Exception): pass


class NotEnoughAP(Exception): pass
