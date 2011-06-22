#!/usr/bin/env python3
import collections

import archon
import archon.objects
import archon.commands
import archon.common
import archon.interface


class battlecommand(archon.commands.command):
    pass


class Effect:
    """
    Defines an effect from battle, such as healing, that is multi-turn.
    """
    # reorder params - should this just be another entity?
    def __init__(self, participle, turns, amount, targetName, target):
        """
        :param participle: A past participle describing the effect (e.g.
                           "healed" or "damaged by fire").
        :param turns: The number of turns to run the effect for. If
                      negative, then the effect is infinite.
        :param amount: The effect magnitude.
        :param targetName: The name of the target.
        :param target: A function, accepting the amount as a parameter, that
                       applies the effect, and optionally returns a value
                       denoting the actual magnitude of the effect.

        When describing an effect, a template of the form "{targetName} was
        {participle} for {magnitude}" will be used.
        """
        self.participle = participle
        self.turns = turns
        self.amount = amount
        self.targetName = targetName
        self.target = target

    @classmethod
    def healing(cls, participle, turns, amount,
                targetEntity, targetAttribute):
        def _healing(amt):
            targetEntity.attributes.damage(-amount, None, targetAttribute)

        return cls(participle, turns, amount,
                   targetEntity.friendlyName, _healing)


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
    for effect in battlecommand('battle').data['effects'][player]:
        magnitude = effect.target(effect.amount) or effect.amount
        effect.turns -= 1
        output.display(
            "{targetName} was {participle} for {magnitude}".format(
                targetName=effect.targetName,
                participle=effect.participle,
                magnitude=magnitude
                )
            )
        if effect.turns == 0:  # negative value -> infinite turns
            battlecommand('battle').data['effects'].remove(effect)


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
def fight(output, context, player, *enemy: archon.commands.find):
    # TODO doesn't check if enemy found was ambiguous
    if not enemy or enemy[0][1].kind != 'enemy':
        raise output.error("You can't fight that.")
    battlecommand('battle').data = {'effects': {
            player: [
                Effect.healing("healed", -1,
                               player.attributes.maxVitals['ap'] / 25,
                               player, 'ap'
                               )
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
        if apCost <= player.attributes.vitals['ap']:
            player.attributes.damage(apCost, None, 'ap')
            if weapon.attributes.hits(multiplier=stats['success']):
                damage = weapon.attributes.damage(multiplier=physicalAcumen)
                fatigue, fatigueTurns = weapon.attributes.fatigue(
                    multiplier=stats['fatigue'])
                realDamage = target.attributes.damage(damage, 'physical')
                output.display("You hit with {} for {:.1f}".format(
                        weapon.friendlyName,
                        realDamage
                        ))
            else:
                output.display("You missed with {}".format(
                        weapon.friendlyName
                        ))
        else:
            output.display("You don't have enough AP to attack.")

    battlecommand.get('enemyTurn')(output, context, player)
