"""Start the authored local application with an explicit private instance."""
import json
from workbench import corpus,runtime


def main():
    code=0;result=None
    try:result=corpus.main()
    except KeyboardInterrupt:result=dict(error='INTERRUPTED');code=130
    except runtime.WorkbenchError as error:result=dict(error=str(error));code=2
    except Exception:result=dict(error='OPERATION_REFUSED');code=2
    finally:
        try:runtime.close()
        except Exception:result=dict(error='INSTANCE_CLOSE_REFUSED');code=2
    if result is not None:print(json.dumps(result,sort_keys=True,ensure_ascii=True,allow_nan=False))
    return code


if __name__=='__main__':raise SystemExit(main())
