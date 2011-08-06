#!/usr/bin/env python3
import argparse

import archon
import archon.common
import archon.datastore


def main():
    datastore = archon.datastore.GameDatastore('data/')
    if 'output' not in datastore:
        datastore.create('output')
    output = datastore['output']
    parser = argparse.ArgumentParser("Generate entities via a template.")
    parser.add_argument('family', nargs=1, help='The item family.')
    parser.add_argument('types', nargs='+', help='Item types.')
    args = parser.parse_args()
    family = datastore['families'].raw(args.family[0], '.json')[1]
    types = []
    for t in args.types:
        types.append(datastore['types'].raw(t, '.json'))
    for name, t in types:
        if name in family['data']['item_types']:
            patch = family['data']['item_types'][name]
            stack = [(patch, t['data'])]
            while stack:
                current, target = stack.pop()
                for key, item in current.items():
                    ty = type(item)
                    if ty == dict:
                        stack.append((item, target[key]))
                    elif ty in (int, float):
                        target[key] += item
                    elif ty == list and len(item) == len(target[key]):
                        target[key] = [x + y for x, y in
                                       zip(item, target[key])]
                for key, item in target.items():
                    if type(item) == str:
                        target[key] = item.format(**family['data'])
            output.save(family['data']['outputName'].format(type=name),
                        t, immediately=True)
            print("Saved entity of type {name} of family {family}".format(
                    name=name, family=family['data']['name_l']))
        else:
            print("Skipped entity type {} (unsupported)".format(name))


if __name__ == '__main__':
    main()
