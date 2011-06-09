#!/usr/bin/env python3
import random

output.display('Welcome to the customization routine.')
name = output.prompt('Name? ')
gender = output.prompt("What's your gender? ")
description = output.prompt('Describe yourself briefly: ')
player.attributes.character.update(
    name=name,
    gender=gender,
    description=description
    )

output.display('''Your acumen in the three traits, Physical, Mental, and
Spiritual, is determined randomly at the beginning. The values will be
generated now. Enter [y/yes] to accept them, or [n/no] to decline and try
again. Only three tries are allowed.
''')

acumen = player.attributes.acumen
for tries in range(3):
    for trait in acumen:
        acumen[trait] = random.randint(10, 40)
    output.display('Try #{}'.format(tries + 1))
    for trait in sorted(acumen):
        output.display('{trait}: {value}'.format(
                trait=trait, value=acumen[trait]
                ))
    if tries != 2 and output.question('Accept? '):
        break
player.attributes.acumen.update(acumen)
context.outputs['on'] = context.entityCache.root['room']
del context.contents['customizer']
output.display(
    'Welcome, {name}, to the demo. Try `go on` to continue.'.format(
        name=name
        )
    )
elapsedTime = 20
