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
    topics = {"visible": {}, "invisible": {}}
    topic, text, actions = '', [], []
    for line in contents.split('\n'):
        if line.startswith(' '):
            line = line.strip()
            if line.startswith('@'):
                tokens = line[1:].split(' ')
                action = tokens[0].strip()
                parameters = [parse(x.strip(', ')) for x in tokens[1:]]
                actions.append((action, parameters))
            else:
                text.append(line.strip())
        else:
            text = ' '.join(text)
            if line.endswith('@invisible'):
                topics['invisible'][topic] = entityhooks.ChatTopic(
                    text, actions)
            topic, text, actions = line.strip(), [], []
    return {"type": "entity",
            "data": {"kind": "chat", "attributes": topics}}
