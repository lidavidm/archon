#!/usr/bin/env python

import sys
import traceback
import archon
import archon.datastore
import archon.objects
import archon.commands

while True:
    print 'Starting a new instance'
    try:
        archon = reload(archon)
        archon.datastore = reload(archon.datastore)
        archon.objects = reload(archon.objects)
        archon.commands = reload(archon.commands)

        ds = archon.datastore.JSONDatastore('demo/')
        entity = ds['entity.json']
        room = ds['room.json']
        interface = archon.objects.ConsoleInterface()

        interface.repl(room, None, archon.commands.command)
    except EOFError, SystemExit:
        print 'Exiting testing loop'
        raise
    except:
        traceback.print_exc()
        raw_input('Press enter to continue')
