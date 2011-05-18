#!/usr/bin/env python

import archon
import archon.datastore
import archon.objects
import archon.commands

ds = archon.datastore.JSONDatastore('demo/')
entity = ds['entity.json']
print entity.capabilities
room = ds['room.json']
interface = archon.objects.ConsoleInterface()
print room.contents

for name in entity.capabilities:
    entity.do(name, interface)

interface.repl(room, None, archon.commands.command)
