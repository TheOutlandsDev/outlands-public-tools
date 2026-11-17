"""Fictional behavior checks alongside the two byte-preserved original tests."""
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.logging_config import JsonFormatter, configure_logging
from app.main import app

KEYS=('APP_NAME','APP_ENVIRONMENT','APP_VERSION','LOG_LEVEL','CONTROL_DB_URL','DATA_ROOT','MANIFEST_ROOT','STAGING_ROOT','RESULTS_ROOT')

@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch, tmp_path):
    for key in KEYS:monkeypatch.delenv(key,raising=False)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    root=logging.getLogger();saved=list(root.handlers);level=root.level
    yield
    root.handlers=saved;root.setLevel(level);get_settings.cache_clear()

def test_original_six_files_preserved():
    root=Path(__file__).resolve().parents[1]
    baseline=json.loads((root/'BASELINE.json').read_bytes())
    assert len(baseline['source_sha256'])==6 and baseline['original_tests']==2
    for name,pin in baseline['source_sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==pin

def test_openapi_describes_only_health_operations():
    with TestClient(app) as client:value=client.get('/openapi.json').json()
    assert value['info']['title']=='Python Data and Query Control Layer'
    assert set(value['paths'])=={'/health/live','/health/ready'}
    assert all(set(v)=={'get'} for v in value['paths'].values())

def test_unknown_route_and_unsupported_method_refused():
    with TestClient(app) as client:
        assert client.get('/fictional-missing').status_code==404
        assert client.post('/health/ready',json={'fictional':True}).status_code==405

def test_default_configuration_is_declarative():
    settings=Settings(_env_file=None)
    assert settings.app_name=='python-control-layer' and settings.app_version=='0.1.0'
    assert settings.app_environment=='development' and settings.log_level=='INFO'
    assert settings.control_db_url=='sqlite:///./runtime/control.db'
    assert settings.data_root=='/data/authoritative' and settings.results_root=='/data/results'

def test_environment_overrides_all_workspace_fields(monkeypatch):
    values={'APP_NAME':'fictional-api','APP_ENVIRONMENT':'fictional','APP_VERSION':'0.1.0-demo','LOG_LEVEL':'DEBUG','CONTROL_DB_URL':'unsupported://fictional','DATA_ROOT':'fictional-data','MANIFEST_ROOT':'fictional-manifests','STAGING_ROOT':'fictional-staging','RESULTS_ROOT':'fictional-results'}
    for key,value in values.items():monkeypatch.setenv(key,value)
    settings=Settings(_env_file=None)
    assert {key:getattr(settings,key.lower()) for key in values}==values

def test_explicit_dotenv_and_environment_precedence(tmp_path,monkeypatch):
    selected=tmp_path/'fictional.env';selected.write_text('APP_ENVIRONMENT=from-file\nAPP_VERSION=demo\nUNKNOWN_FICTIONAL=ignored\n',encoding='utf-8')
    monkeypatch.setenv('APP_ENVIRONMENT','from-environment')
    settings=Settings(_env_file=selected)
    assert settings.app_environment=='from-environment' and settings.app_version=='demo'
    assert not hasattr(settings,'unknown_fictional')

def test_cached_settings_require_explicit_refresh(monkeypatch):
    monkeypatch.setenv('APP_ENVIRONMENT','first');first=get_settings()
    monkeypatch.setenv('APP_ENVIRONMENT','second')
    assert get_settings() is first and get_settings().app_environment=='first'
    get_settings.cache_clear();assert get_settings().app_environment=='second'

def test_invalid_log_level_prevents_startup(monkeypatch):
    monkeypatch.setenv('LOG_LEVEL','FICTIONAL_INVALID_LEVEL')
    with pytest.raises(ValueError):
        with TestClient(app):pass

def test_lifecycle_emits_json_start_and_stop(capsys):
    with TestClient(app) as client:assert client.get('/health/live').json()=={'status':'alive'}
    values=[json.loads(line) for line in capsys.readouterr().out.splitlines() if line]
    messages=[v['message'] for v in values]
    assert messages.count('application_started')==messages.count('application_stopped')==1
    for value in values:
        assert datetime.fromisoformat(value['timestamp']).utcoffset()==timezone.utc.utcoffset(None)

def test_formatter_keeps_message_newline_inside_json():
    record=logging.LogRecord('fictional',logging.INFO,'fictional.py',1,'First\nsecond %s',('line',),None)
    raw=JsonFormatter().format(record)
    assert '\n' not in raw and json.loads(raw)['message']=='First\nsecond line'

def test_formatter_exception_field_is_explicit():
    try:raise ValueError('fictional failure')
    except ValueError:
        import sys
        record=logging.LogRecord('fictional',logging.ERROR,'fictional.py',1,'Controlled failure',(),sys.exc_info())
    value=json.loads(JsonFormatter().format(record))
    assert 'ValueError: fictional failure' in value['exception']

def test_formatter_does_not_export_arbitrary_extra_fields():
    record=logging.LogRecord('fictional',logging.INFO,'fictional.py',1,'Message',(),None)
    record.app_version='fictional-extra'
    value=json.loads(JsonFormatter().format(record))
    assert set(value)=={'timestamp','level','logger','message'}

def test_logging_configuration_replaces_process_root_handlers():
    root=logging.getLogger();root.handlers=[logging.NullHandler()]
    configure_logging('debug')
    assert len(root.handlers)==1 and isinstance(root.handlers[0],logging.StreamHandler)
    assert isinstance(root.handlers[0].formatter,JsonFormatter) and root.level==logging.DEBUG

def test_readiness_does_not_verify_storage_or_create_directories(tmp_path,monkeypatch):
    monkeypatch.setenv('CONTROL_DB_URL','unsupported://fictional-unavailable')
    for key in ('DATA_ROOT','MANIFEST_ROOT','STAGING_ROOT','RESULTS_ROOT'):monkeypatch.setenv(key,str(tmp_path/key.lower()))
    before=set(tmp_path.iterdir())
    with TestClient(app) as client:assert client.get('/health/ready').json()=={'status':'ready'}
    assert set(tmp_path.iterdir())==before
