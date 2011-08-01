import collections
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
    conversation = npc.attributes.conversation
    while True:
        choice = output.menu('{key}. {description}', '> ', 'Invalid topic.',
                             *conversation.topics)
        if conversation.isEnd(choice):
            break
        choice = conversation.topicIndex[choice][1]
        output.display(choice.contents)
        output.display("")
        for action, params in choice.actions:
            conversation.actions.get(action, lambda *args: None)(
                output, context, player, *params)
