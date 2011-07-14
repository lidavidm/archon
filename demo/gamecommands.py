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
    dialouge = npc.entityCache.lookup(npc.attributes['dialouge'][0])
    dialouge = dialouge.attributes
    topics = dialouge['visible']
    topicIndex = collections.OrderedDict(
        enumerate(dialouge['visible'].items()))
    topicIndex[len(topicIndex)] = ("bye", None)
    while True:
        choice = output.menu('{key}. {description}', '> ', 'Invalid topic.',
                             *(topic[0] for topic in topicIndex.values()))
        if choice == len(topicIndex) - 1:
            break
        choice = topicIndex[choice][1]
        output.display(choice.contents)
        output.display("")
        for action, params in choice.actions:
            command.get('chat').data.get(action, lambda *args: None)(
                dialouge, topicIndex, *params)


def chat_visible(dialouge, topicIndex, *topics):
    topicIndex.popitem()  # remove "bye"
    base = len(topicIndex)
    currentTopics = [topic[0] for topic in topicIndex.values()]
    topicIndex.update({base + offset: (topic, dialouge['invisible'][topic])
                       for offset, topic in enumerate(topics)
                       if topic in dialouge['invisible'] and
                       topic not in currentTopics})
    topicIndex[len(topicIndex)] = ("bye", None)


command.get('chat').data = {
    'visible': chat_visible
}
