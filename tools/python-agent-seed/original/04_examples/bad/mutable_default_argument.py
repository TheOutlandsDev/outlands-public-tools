"""Bad example: mutable default argument."""


def add_tag(name, tags=[]):
    tags.append(name)
    return tags


# Problem:
# The same list is reused across calls. Use None as the default and allocate a new list inside the function.
