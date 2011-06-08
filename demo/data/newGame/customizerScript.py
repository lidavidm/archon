#!/usr/bin/env python
output.display('Welcome to the customization routine.')
name = output.prompt('Name? ')
gender = output.prompt("What's your gender? ")
description = output.prompt('Describe yourself briefly: ')
player["character"].update(
    name=name,
    gender=gender,
    description=description
    )
context.outputs['on'] = context.entityCache.root['room']
del context.contents['customizer']
output.display(
    'Welcome, {name}, to the demo. Try `go on` to continue.'.format(
        name=name
        )
    )
elapsedTime = 20
