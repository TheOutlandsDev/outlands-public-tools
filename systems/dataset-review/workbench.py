"""Private Dataset Review Workbench entry point; legacy review_store.py remains."""
import json
import sys
from dataset_workbench import cli
if __name__=='__main__':
    try:result=cli.main();code=0
    except KeyboardInterrupt:result={'error':'INTERRUPTED'};code=130
    except Exception:result={'error':'OPERATION_REFUSED'};code=2
    if result is not None:print(json.dumps(result,sort_keys=True,ensure_ascii=True,allow_nan=False))
    sys.exit(code)
