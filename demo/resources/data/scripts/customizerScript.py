#!/usr/bin/env python3
import random
import base64
import datetime


def main(output, context, player):
    output.display('Welcome to the customization routine.')
    name = output.prompt('Name? ')
    gender = output.prompt("What's your gender? ")
    description = output.prompt('Describe yourself briefly: ')
    player.attributes.character.update(
        name=name,
        gender=gender,
        description=description
        )
    player.name = base64.urlsafe_b64encode(
        player.attributes.character['name'].encode('utf-8')
        )

    output.display('''Your acumen in the three traits, Physical, Mental, and
    Spiritual, is determined randomly at the beginning. The values will be
    generated now. Enter [y/yes] to accept them, or [n/no] to decline and
    try again. Only three tries are allowed.
    ''')

    acumen = player.attributes.acumen
    statFormat = '  {stat}: {value[0]:.2} to {value[1]:.2} multiplier'
    for tries in range(3):
        for trait in acumen:
            acumen[trait] = random.randint(10, 40)
        output.display('Try #{}'.format(tries + 1))
        player.attributes.acumen.update(acumen)
        stats = player.attributes.stats
        for trait in sorted(acumen):
            output.display('{trait}: {value}'.format(
                    trait=trait, value=acumen[trait]
                    ))
            for stat in sorted(stats[trait]):
                output.display(statFormat.format(
                        stat=stat, value=stats[trait][stat]
                        ))
        if tries != 2 and output.question('Accept? '):
            break

    player.attributes.vitals.update(player.attributes.maxVitals)

    context.outputs['on'] = context.entityCache.root['data.areas.room']
    context.remove(context.naturalFind('customizer'))
    output.display(
        'Welcome, {name}, to the demo. Try `go on` to continue.'.format(
            name=name
            )
        )
    return datetime.timedelta(minutes=20)
