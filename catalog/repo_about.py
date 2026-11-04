"""Check the public GitHub About description against catalog scope and live metadata."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent


class AboutError(ValueError):
    pass


def check(live=False):
    about = json.loads((HERE/'repo-about.json').read_text(encoding='utf-8'))
    catalog = json.loads((HERE/'registry.json').read_text(encoding='utf-8'))
    if set(about) != {'schema', 'repository', 'description', 'catalog_group_terms'} or about['schema'] != 1:
        raise AboutError('ABOUT_SCHEMA_INVALID')
    if about['repository'] != 'TheOutlandsDev/outlands-public-tools':
        raise AboutError('REPOSITORY_INVALID')
    description = about['description']
    if type(description) is not str or not 40 <= len(description) <= 250 or '\n' in description:
        raise AboutError('DESCRIPTION_INVALID')
    groups = {row['group'] for row in catalog['components']}
    terms = about['catalog_group_terms']
    if type(terms) is not dict or set(terms) != groups:
        raise AboutError('CATALOG_GROUP_COVERAGE_CHANGED')
    for term in terms.values():
        if type(term) is not str or len(term) < 3 or term.casefold() not in description.casefold():
            raise AboutError('DESCRIPTION_GROUP_MISSING')
    if live:
        request = Request('https://api.github.com/repos/'+about['repository'], headers={
            'Accept':'application/vnd.github+json',
            'User-Agent':'outlands-public-tools-about-check',
            'Cache-Control':'no-cache',
        })
        with urlopen(request, timeout=20) as response:
            remote = json.load(response)
        if remote.get('full_name') != about['repository'] or remote.get('description') != description:
            raise AboutError('LIVE_DESCRIPTION_MISMATCH')
    return {'status':'PASS','catalog_groups':len(groups),'description':description,'live_checked':live}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Compare the public GitHub About value with repo-about.json.')
    args = parser.parse_args(argv)
    try:
        result = check(args.live)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (AboutError, OSError, ValueError, TimeoutError) as error:
        print(json.dumps({'status':'ERROR','code':str(error) if isinstance(error, AboutError) else 'ABOUT_CHECK_UNAVAILABLE'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
