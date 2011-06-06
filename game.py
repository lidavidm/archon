#!/usr/bin/env python
import sys

import archon
import archon.common
import archon.datahandlers
import archon.datastore
import archon.objects
import archon.interface
import archon.commands

if __name__ == '__main__':
    cache = archon.datastore.LazyCacheDatastore()
    cache2 = archon.datastore.LazyCacheDatastore()
    ds = archon.datastore.GameDatastore('demo/data', cache)
    save = archon.datastore.GameDatastore('demo/save', cache2)
    room = None
    player = save['player_template']
    interface = archon.interface.ConsoleInterface()
    while True:
        interface.display('Welcome to the demo.')
        interface.display('Choose an option:')
        choice = interface.menu('[{option}]: {description}', '> ',
                                **{'0': 'New Game',
                                '1': 'Load Game',
                                '2': 'Exit'})
        if choice == '0':
            room = ds['newGame.newGame']
        elif choice == '1':
            print 'That is not supported at this time.'
            sys.exit()
        elif choice == '2':
            sys.exit()
        interface.repl(room, player, archon.commands.command)

