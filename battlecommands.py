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


# XXX some way of hiding this from the player
@battlecommand('applyBattleEffects')
def applyBattleEffects(output, context, player):
    effects = battlecommand('battle').data['effects']
    for target in effects:
        for effect in effects[target]:
            if effect.hit:
                target.attributes.damage(effect.magnitude,
                                         **effect.target._asdict())
                output.display(
                    output.format(
                        effect.message('success'),
                        user='second_person',
                        target='second_person'
                        )
                    )
            effect.turns -= 1
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
    vitals = player.attributes.vitals
    output.promptData.update(
        turn='Turn {}'.format(context.attributes['turn']),
        hp='HP {:.1f}'.format(vitals['health']),
        ap='AP {:.1f}'.format(vitals['ap'])
        )
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
            player: [entityhooks.EffectEntityHook.healingT(
                    player.attributes.vitals['ap'] / 30, -1,
                    'vital:ap', target=player
                    )]
            },
        'enemies': [x[1] for x in enemies]  # get only the entities
        }
    olddata = output.promptData.copy()
    output.promptData.clear()
    output.repl(scene, player, battlecommand)
    output.promptData.update(olddata)
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
        effect = weaponEffect.instance(physicalAcumen, stats,
                                       user=player, target=target)
        try:
            realDamage = applyEffect(player, target, effect)
            battlecommand('battle').data['effects'][player].append(
                weaponEffect.fatigue(stats['fatigue'], target=player))
            output.display(effect.message('success'))
        except EffectMissed:
            output.display(effect.message('failure'))
        except NotEnoughAP:
            output.display("You don't have enough AP to attack.")

    battlecommand.get('enemyTurn')(output, context, player)


def applyEffect(user, target, effect):
    if effect.drain <= user.attributes.vitals['ap']:
        user.attributes.damage(effect.drain, 'vital', None, 'ap')
        if effect.hit:
            return target.attributes.damage(
                effect.magnitude, **effect.target._asdict())
        else:
            raise EffectMissed
    else:
        raise NotEnoughAP


class EffectMissed(Exception): pass


class NotEnoughAP(Exception): pass
