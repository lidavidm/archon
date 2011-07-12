#!/usr/bin/env python3
import sys
import datetime

import archon
import archon.common
import archon.datahandlers
import archon.datastore
import archon.objects
import archon.interface
import archon.commands

import data
import battlecommands
import entityhooks

if __name__ == '__main__':
    ds = archon.datastore.GameDatastore('resources')
    data = ds['data']
    save = ds['save']
    metadata = data['metadata']  # load the metadata
    room = None
    player = archon.objects.PlayerEntityHook.defaultInstance()
    interface = archon.interface.ConsoleInterface(
        permissions={'debug': True},
        messageTemplates=data['messages']
        )

    while True:
        interface.display('Welcome to the demo.')
        interface.display('Choose an option:')
        choice = interface.menu('[{option}]: {description}', '> ',
                                **{'0': 'New Game',
                                '1': 'Load Game',
                                '2': 'Exit'})
        if choice == '0':
            room = data['areas.newGame.newGame']
        elif choice == '1':
            print('That is not supported at this time.')
            sys.exit()
        elif choice == '2':
            sys.exit()
        room.enter(datetime.datetime(1000, 1, 1, 12, 0))
        interface.repl(room, player, archon.commands.command)
