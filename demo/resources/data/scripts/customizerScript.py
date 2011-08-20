#!/usr/bin/env python3
classes = {
    "Hunter": [{"physical": 50, "mental": 30, "spiritual": 30},
               {"body": "data.items.armor.leather_body",
                "legs": "data.items.armor.leather_legs",
                "feet": "data.items.armor.leather_boots",
                "left hand": "data.items.weapons.iron_dagger"},
               {}],
    "Mage": [{"physical": 30, "mental": 50, "spiritual": 30},
             {"body": "data.items.armor.mage_blouse",
              "legs": "data.items.armor.mage_skirt",
              "feet": "data.items.armor.leather_boots",
              "left hand": "data.items.weapons.wooden_staff"},
             {}],
    "Swordfighter": [{"physical": 50, "mental": 30, "spiritual": 30},
                     {"body": "data.items.armor.chain_body",
                      "legs": "data.items.armor.chain_legs",
                      "feet": "data.items.armor.chain_boots",
                      "left hand": "data.items.weapons.iron_sword_short"},
                     {}]
}


def main(output, context, player, npc, conversation):
    conversation.removeTopic('greetings')
    output.display('I see you appear to be a...')
    choices = list(classes.keys())
    prof = output.menu('[{key}]: {description}', '> ', 'Invalid choice.',
                       *choices)
    acumen, equipment, inventory = classes[choices[prof]]
    player.attributes.acumen.update(acumen)
    equip = {slot: player.entityCache.lookup(loc)
             for slot, loc in equipment.items()}
    player.attributes.equip.update(equip)
    player.attributes.inventory.extend(inventory)
    statFormat = '  {stat}: {value[0]:.2} to {value[1]:.2} multiplier'
    stats = player.attributes.stats
    for trait in sorted(player.attributes.acumen):
        output.display('{trait}: {value}'.format(
                trait=trait, value=acumen[trait]
                ))
        for stat in sorted(stats[trait]):
            output.display(statFormat.format(
                    stat=stat, value=stats[trait][stat]
                    ))
    player.attributes.vitals.update(player.attributes.maxVitals)
