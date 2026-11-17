import json


class JsonLoaderError(Exception):
    pass


def load_json_object(path):
    with open(path) as f:
        return json.loads(f.read())
