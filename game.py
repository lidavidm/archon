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
    ds = archon.datastore.GameDatastore(
        'demo/data',
        archon.datastore.LazyCacheDatastore
        )
    save = archon.datastore.GameDatastore(
        'demo/save',
        archon.datastore.LazyCacheDatastore
        )
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

