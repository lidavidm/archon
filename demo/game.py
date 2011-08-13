#!/usr/bin/env python3
import sys
import uuid
import base64
import datetime

import archon
import archon.common
import archon.datahandlers
import archon.datastore
import archon.objects
import archon.interface
import archon.commands

import datahandlers
import gamecommands
import battlecommands
import entityhooks

if __name__ == '__main__':
    ds = archon.datastore.GameDatastore('resources')
    data = ds['data']
    save = ds['save']
    metadata = data['metadata']  # load the metadata
    room = None

    interface = archon.interface.ConsoleInterface(
        permissions={'debug': True},
        messageTemplates=data['messages']['templates']
        )

    while True:
        interface.display('Welcome to the demo.')
        interface.display('Choose an option:')
        choice = interface.menu('[{key}]: {description}', '> ',
                                'Invalid choice.',
                                'New Game', 'Load', 'Quit')
        if choice == 0:
            room = data['areas.marcellus.marcellia.square']
            player = archon.objects.PlayerEntityHook.defaultInstance()
            player.name = base64.urlsafe_b64encode(
                uuid.uuid4().bytes).decode('utf-8')
            player.entityCache = save.create(player.name)
            player.entityCache.create("instances")
        elif choice == 1:
            players = {}
            for key in save.keys():
                savegame = save[key]
                player = savegame.raw('player', '.json')[1]
                player = player['data']['attributes']['character']['name']
                gameVars = savegame.raw('gameVars', '.json')[1]
                roomName = gameVars['data']['lastRoom'].rsplit('.', 1)[1]
                players["{} ({})".format(player, roomName)] = key
            choice = interface.menu('[{key}]: {description}', '> ',
                                    'Invalid save file.',
                                    *players.keys())
            savegame = save[players[list(players.keys())[choice]]]
            gameVars = savegame['gameVars']
            player = savegame['player']
            patches = savegame['patches']
            room = data.lookup(gameVars['lastRoom'])
        elif choice == 2:
            sys.exit()
        archon.objects.Entity.instances = player.entityCache['instances']
        room.enter(datetime.datetime(1000, 1, 1, 12, 0))
        interface.repl(room, player, archon.commands.command)
