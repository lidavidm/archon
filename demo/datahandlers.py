import re
import archon.datahandlers

import entityhooks


def parse(item):
    try:
        return float(item)
    except ValueError:
        if item.isnumeric():
            return int(item)
        return item


@archon.datahandlers.dataparser('.chat')
def chatType(contents):
    actionRegex = re.compile('@([\w]+) *([\w ,]*)')
    topics = {"invisible": {}, "visible": {}}
    topic, text, actions = '', [], []
    for line in contents.split('\n'):
        if line.startswith(' '):
            line = line.strip()
            if line.startswith('@'):
                actions.append(line)
            else:
                text.append(line)
        else:
            if topic:
                category = 'visible'
                if '@invisible' in topic:
                    category = 'invisible'
                    topic = topic[:-10].strip()
                text = ' '.join(text)
                parsedActions = []
                for action in actions:
                    groups = actionRegex.match(action).groups()
                    parsedActions.append(
                        (groups[0],
                         [x.strip() for x in groups[1].split(',')]))
                topics[category][topic] = entityhooks.ChatTopic(
                    text, parsedActions)
            topic, text, actions = line.strip(), [], []
    return {"type": "entity",
            "data": {"kind": "chat", "attributes": topics}}
