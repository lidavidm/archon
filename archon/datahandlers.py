import json
import warnings

import archon.common
import archon.objects
import archon.scripting


# Types dictate loading, kind denotes semantic data ("room" vs "indoors")
class dataloader(archon.common.denoter):
    """Denotes a function that takes JSON and creates an object."""
    functions = {}


class dataparser(archon.common.denoter):
    """Denotes a function that converts a file to a JSON-like representation
    of the data."""
    functions = {}


class dataserializer(archon.common.denoter):
    """Denotes a function that takes an object and creates JSON.

    Private properties should not be needed by this function; ideally, the
    public API of the object should expose all the needed information to
    save it to disk.
    """
    functions = {}


@dataparser('.json')
def jsonType(contents):
    try:
        data = json.loads(contents)
        assert 'type' in data
        assert 'data' in data
        return data
    except ValueError:
        warnings.warn("Error loading JSON data!",
                      RuntimeWarning, stacklevel=2)
        return None
    except AssertionError:
        warnings.warn('JSON data is not well-formed!',
                      RuntineWarning, stacklevel=2)
        return None


@dataparser('.py')
def pythonType(contents):
    return {"type": "script", "data": contents}


@dataloader('metadata')
def metadata(key, data, cache):
    for kind, data in data.items():
        if kind == "entity_templates":
            for entityKind, templates in data.items():
                try:
                    ehook = archon.objects.EntityHook.getHook(entityKind)
                    for key, template in templates.items():
                        templates[key] = cache.lookup(template)
                    ehook.templates = templates
                except archon.objects.EntityHookNotFoundError:
                    warnings.warn(entityKind +
                                  " entity hook not found for templating!")
        elif kind == "metadata":
            for path in data:
                cache.lookup(path)  # side effect is what matters here
        else:
            warnings.warn(kind + " metadata kind not recognized!")
    return data


@dataloader('entity')
def entity(key, data, cache):
    kind = data['kind']
    attributes = data['attributes']
    for attr, value in attributes.items():
        if (isinstance(value, dict) and
            'template' in value and 'data' in value):  # embedded template
            try:
                template = cache.lookup(value['template']).copy()
                # deal with mutables, use templating mechanism
                template.attributes.attributes.update(
                    template.attributes.viaTemplate(value['data']))
                # XXX this would be more resilient if it recursed into
                # subvalues so that they could also be used as defaults
                attributes[attr] = template
            except KeyError:  # didn't find entity
                warnings.warn(
                    "Error templating {}".format(value['template']),
                    RuntimeWarning, stacklevel=2
                    )
    entity = archon.objects.Entity(key, kind, cache, data['attributes'])
    return entity


@dataloader('area')
def area(key, data, cache):
    name = data['name']
    attributes = {'name': name}
    attributes.update(data['attributes'])
    area = archon.objects.Entity(key, cache, 'area', attributes)
    area.entityCache = cache
    return area


@dataloader('room')
def room(key, data, cache):
    description = data['describe']
    room = archon.objects.Room(key, description, cache)

    for name, val in data['attributes'].items():
        room.attributes[name] = val

    contents = []
    for eKey, eData in data['contents'].items():
        entityInfo = {}
        entityLocation = eData['entity']

        if ',' in eKey:
            eKey, prefix = eKey.split(',')
            prefix = prefix.strip()
            eKey = archon.objects.EntityKey(eKey, prefix)
            entityInfo['prefix'] = prefix

        if 'options' in eData:
            eData['options'] = eData['options'].split(',')
        entityInfo.update(eData)
        del entityInfo['entity']  # this key doesn't need to be there
        contents.append((entityLocation, eKey, entityInfo))
    ids = [eKey for _, eKey, _ in contents]
    for eLocation, eKey, eInfo in contents:
        # identity (or key) is not unique, no prefix and the key collides
        # with an identity
        if 'prefix' not in eInfo and ids.count(eKey) > 1:
            # we need to generate a prefix
            eInfo['prefix'] = ('yet another ' *
                               (ids.count(Key) - 1)).strip()

    for eLocation, eKey, eInfo in contents:
        room.add(eLocation, eKey, **eInfo)

    # Load the area if present.
    if 'area' in cache:
        room.area = cache['area']

    # Unlike the others, this MUST be here to break circular references when
    # loading rooms (although the thunk is present in the cache,
    # dereferencing it will cause a loop where we continually reload the
    # same room)
    cache.add(key, room)

    for direction, target in data['outputs'].items():
        try:
            troom = cache.lookup(target)
            room.addRoom(direction, troom)
        except KeyError:
            raise ValueError("Room {} not found!".format(target))
    return room


@dataloader('data')
def data(key, data, cache):
    """
    Loads unstructured JSON data, essentially.
    """
    # Possibly look for "#reference(key)" strings and replace them so that
    # links to other data files can be made?
    return data


@dataloader('script')
def script(key, data, cache):
    """Loads a Python script."""
    return archon.scripting.Script(compile(data, '<string>', 'exec'))
