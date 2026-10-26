"""Create fictional saved telemetry in a fresh private directory. Original MIT."""
from pathlib import Path
import json
import os
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser, TextError, canonical_directory, cli_error, local_path, no_links, require


def row(kind, **payload): return {'type': kind, 'payload': payload}


def encode(rows): return ('\n'.join(json.dumps(value, separators=(',',':')) for value in rows)+'\n').encode('utf-8')


def fixtures():
    clean = [row('raid_start',map='FictionalOrchard',raid_seconds=0),
             row('snapshot',player_count=2,bot_count=4,tracking={'active_count':3},
                 line_of_sight=[{'main_can_see_bot':True},{'main_can_see_bot':False}],raid_seconds=0.1),
             row('snapshot',player_count=4,tracking={'active_count':1}),
             row('snapshot',bot_count=8,line_of_sight=[],raid_seconds=0.3),
             row('tracking_assigned'), row('raid_end',dropped_lines=0,raid_seconds=1.0)]
    review = [row('snapshot',player_count=True,bot_count=3,tracking=None),
              row('raid_end',dropped_lines=3),row('raid_end',dropped_lines=3)]
    return {'clean.jsonl':encode(clean), 'review.jsonl':encode(review)+b'{unfinished\n',
            'missing-fields.jsonl':encode([row('snapshot',player_count=0),row('snapshot')])}


def main(argv=None):
    parser=Parser(description=__doc__);parser.add_argument('--output',required=True)
    try:
        args=parser.parse_args(argv);output=local_path(args.output)
        parent=canonical_directory(output.parent);require(not output.exists() and not output.is_symlink(),'OUTPUT_EXISTS')
        output=parent/output.name;output.mkdir(mode=0o700,exist_ok=False)
        for name,data in fixtures().items():
            no_links(output)
            fd=os.open(output/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0),0o600)
            with os.fdopen(fd,'wb') as stream:stream.write(data)
        print(json.dumps({'status':'FICTIONAL_EXAMPLES_CREATED','files':3}));return 0
    except (TextError,OSError,ValueError) as error:return cli_error(error)


if __name__=='__main__':raise SystemExit(main())
