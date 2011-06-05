#!/usr/bin/env python

import sys
import traceback
import archon
import archon.common
import archon.dataloaders
import archon.datastore
import archon.objects
import archon.interface
import archon.commands

while True:
    print 'Starting a new instance'
    try:
        archon = reload(archon)
        # XXX replace this
        archon.common = reload(archon.common)
        archon.dataloaders = reload(archon.dataloaders)
        archon.datastore = reload(archon.datastore)
        archon.objects = reload(archon.objects)
        archon.interface = reload(archon.interface)
        archon.commands = reload(archon.commands)

        cache = archon.datastore.LazyCacheDatastore()
        cache2 = archon.datastore.LazyCacheDatastore()
        ds = archon.datastore.GameDatastore('demo/data', cache)
        save = archon.datastore.GameDatastore('demo/save', cache2)
        room = ds['room']
        player = save['player']
        interface = archon.interface.ConsoleInterface()

        interface.repl(room, None, archon.commands.command)
    except (EOFError, SystemExit):
        print 'Exiting testing loop'
        break
    except:
        traceback.print_exc()
        raw_input('Press enter to continue')
