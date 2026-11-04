"""Bounded, value-free element-shape summary for one supplied XML document."""
from collections import defaultdict

import toolkit as t


def profile(text):
    t.require(type(text) is str, 'XML_TEXT_INVALID')
    try:
        raw = text.encode('utf-8')
    except UnicodeError:
        raise t.Rejected('XML_TEXT_INVALID') from None
    t.require(len(raw) <= 4096, 'XML_TEXT_LIMIT')
    root = t.xml(raw)
    paths = defaultdict(lambda: {'occurrences': 0, 'attributes': defaultdict(int),
                                 'direct_text': 0, 'minimum_children': None,
                                 'maximum_children': 0})
    pending = [(root, (), 0)]
    nodes = 0
    while pending:
        node, parent, depth = pending.pop()
        nodes += 1
        t.require(nodes <= 512 and depth <= 12, 'XML_STRUCTURE_LIMIT')
        t.require(type(node.tag) is str and len(node.tag) <= 256, 'XML_TAG_LIMIT')
        path = parent + (node.tag,)
        row = paths[path]
        row['occurrences'] += 1
        for key in node.attrib:
            t.require(len(key) <= 256, 'XML_ATTRIBUTE_LIMIT')
            row['attributes'][key] += 1
        row['direct_text'] += bool((node.text and node.text.strip()) or
                                   any(child.tail and child.tail.strip() for child in node))
        children = len(node)
        row['minimum_children'] = children if row['minimum_children'] is None else min(row['minimum_children'], children)
        row['maximum_children'] = max(row['maximum_children'], children)
        pending.extend((child, path, depth + 1) for child in node)
        t.require(len(paths) <= 256, 'XML_PATH_LIMIT')
    shape = {'element_count': nodes, 'path_count': len(paths),
             'paths': [{'path': list(path), 'occurrences': row['occurrences'],
                        'attributes': dict(sorted(row['attributes'].items())),
                        'direct_text': row['direct_text'],
                        'minimum_children': row['minimum_children'],
                        'maximum_children': row['maximum_children']}
                       for path, row in sorted(paths.items())]}
    return shape, t.digest(t.encode(shape)), t.digest(raw)
