import archon
import archon.objects
import archon.commands

from archon.commands import find, command


@command('chat', 'talk')
def chat(output, context, player, *npc: find):
    if not npc:
        raise output.error("Who did you want to talk to?")
    elif len(npc) > 1:
        raise output.error("You can only talk to one NPC at a time.")
    data, npc = npc[0]
    if not npc.attributes.get("dialouge"):
        raise output.error("That person has nothing to say.")
    dialouge = npc.entityCache.lookup(npc.attributes['dialouge'][0])
    dialouge = dialouge.attributes
    while True:
        topics = dialouge['visible']
        topicIndex = list(dialouge['visible'].keys())
        choice = output.menu('{key}. {description}', '> ', 'Invalid topic.',
                             *topics.keys())
        output.display(dialouge['visible'][topicIndex[choice]].contents)
