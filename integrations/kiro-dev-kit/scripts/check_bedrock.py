"""Validate a local pairing plan or exercise the SDK using in-memory HTTP only."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import re
import sys


def exact_fields(value, names):
    if not isinstance(value, dict) or set(value) != set(names):
        raise ValueError("Unexpected configuration fields; use the supplied template without credentials")


def model_id(value):
    return (isinstance(value, str) and 0 < len(value) <= 128
            and re.fullmatch(r"[A-Za-z0-9_.:/-]+", value) is not None
            and "://" not in value)


def load_plan(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate configuration field")
            result[key] = value
        return result
    raw = Path(path).read_bytes()
    if len(raw) > 65536:
        raise ValueError("Pairing plan is too large")
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("Pairing plan must be UTF-8 JSON") from None


def check_plan(plan):
    exact_fields(plan, ("schema_version", "kiro", "bedrock"))
    if type(plan["schema_version"]) is not int or plan["schema_version"] != 1:
        raise ValueError("Unsupported pairing schema")
    kiro, bedrock = plan["kiro"], plan["bedrock"]
    exact_fields(kiro, ("approved_model_ids", "selected_model_id"))
    exact_fields(bedrock, ("enabled", "endpoint", "region", "model_id", "auth_method", "profile_name"))
    available, selected = kiro["approved_model_ids"], kiro["selected_model_id"]
    if not isinstance(available, list) or len(available) > 100 or any(not model_id(x) for x in available):
        raise ValueError("Kiro model inventory is invalid")
    if len(set(available)) != len(available):
        raise ValueError("Kiro model inventory contains duplicates")
    if selected is not None and (not model_id(selected) or selected not in available):
        raise ValueError("Selected Kiro model is absent from the supplied approved inventory")
    if type(bedrock["enabled"]) is not bool:
        raise ValueError("Bedrock enabled must be a boolean")
    if bedrock["endpoint"] not in ("runtime", "mantle"):
        raise ValueError("Choose Runtime or Mantle")
    if bedrock["auth_method"] not in ("unconfigured", "aws-profile", "environment", "bedrock-api-key"):
        raise ValueError("Unsupported declared authentication method")
    profile = bedrock["profile_name"]
    if profile is not None and (not isinstance(profile, str) or re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", profile) is None):
        raise ValueError("Invalid profile-name declaration; never place credentials in this plan")
    if profile is not None and bedrock["auth_method"] != "aws-profile":
        raise ValueError("A profile name requires the aws-profile authentication method")
    region, model = bedrock["region"], bedrock["model_id"]
    if region is not None and (not isinstance(region, str) or re.fullmatch(r"[a-z]{2}(?:-gov)?-[a-z]+-\d", region) is None):
        raise ValueError("Invalid AWS Region declaration")
    if model is not None:
        prefix = r"(?:us|global)\.openai\." if bedrock["endpoint"] == "runtime" else r"openai\."
        if not model_id(model) or re.fullmatch(prefix + r"[A-Za-z0-9_.-]+", model) is None:
            raise ValueError("Model identifier does not match the selected Bedrock endpoint")
    issues = []
    url = None
    if bedrock["enabled"]:
        if not region or not model:
            issues.append("BEDROCK_REGION_AND_MODEL_REQUIRED")
        if bedrock["auth_method"] == "unconfigured":
            issues.append("BEDROCK_AUTH_METHOD_REQUIRED")
        if bedrock["auth_method"] == "aws-profile" and not profile:
            issues.append("BEDROCK_PROFILE_NAME_REQUIRED")
        if bedrock["endpoint"] == "mantle" and model in ("openai.gpt-6-sol", "openai.gpt-6-luna") and region != "us-east-1":
            issues.append("DOCUMENTED_MANTLE_REGION_MISMATCH")
        if bedrock["endpoint"] == "mantle" and model == "openai.gpt-6-astra" and region != "us-west-2":
            issues.append("DOCUMENTED_MANTLE_REGION_MISMATCH")
        if region:
            host = f"bedrock-runtime.{region}.amazonaws.com" if bedrock["endpoint"] == "runtime" else f"bedrock-mantle.{region}.api.aws"
            url = f"https://{host}/openai/v1"
    return {
        "format": "kiro-bedrock-plan-v1", "offline": True, "network_requests": 0,
        "plan_complete": selected is not None and not issues,
        "kiro": {"inventory_supplied": bool(available), "model_selection_declared": selected is not None,
                 "sign_in": "NOT_VERIFIED", "model_access": "NOT_VERIFIED"},
        "direct_bedrock": {"requested": bedrock["enabled"], "endpoint": bedrock["endpoint"],
                           "derived_base_url": url, "auth_method_declared": bedrock["auth_method"],
                           "profile_name_supplied": profile is not None,
                           "credentials": "NOT_READ", "iam_and_model_access": "NOT_VERIFIED",
                           "region_model_availability": "NOT_VERIFIED"},
        "issues": issues, "ready_for_live_work": False,
        "note": "Kiro sign-in and direct Bedrock SDK access are separate qualifications. No credentials are accepted or resolved here."
    }


def probe_sdk():
    """Four real SDK serializations, all intercepted in memory, with dummy auth."""
    import os
    from unittest.mock import patch
    from openai import OpenAI
    from openai.providers import bedrock
    import httpx2

    checks = []
    def require(condition):
        if not condition:
            raise ValueError("Offline SDK request did not match its expected contract")
    # Clear all ambient credentials/proxy settings, block socket creation, and
    # supply explicit dummy auth. The AWS credential chain is never requested.
    with patch.dict(os.environ, {}, clear=True), patch("socket.socket", side_effect=RuntimeError("Network forbidden")), patch("socket.create_connection", side_effect=RuntimeError("Network forbidden")):
        for endpoint in ("runtime", "mantle"):
            for auth in ("bearer", "sigv4"):
                model = "us.openai.gpt-6-sol" if endpoint == "runtime" else "openai.gpt-6-sol"
                expected_host = "bedrock-runtime.us-east-1.amazonaws.com" if endpoint == "runtime" else "bedrock-mantle.us-east-1.api.aws"
                intercepted = []

                def respond(request):
                    body = json.loads(request.content)
                    authorization = request.headers.get("authorization", "")
                    require(request.url.host == expected_host)
                    require(request.url.path == "/openai/v1/responses")
                    require(body["model"] == model)
                    require(authorization.startswith("Bearer ") if auth == "bearer" else authorization.startswith("AWS4-HMAC-SHA256 "))
                    if auth == "sigv4":
                        service = "bedrock" if endpoint == "runtime" else "bedrock-mantle"
                        require(f"/{service}/aws4_request" in authorization)
                    intercepted.append(True)
                    return httpx2.Response(200, json={
                        "id": "resp_offline", "object": "response", "created_at": 0,
                        "model": model, "status": "completed", "output": [{
                            "id": "msg_offline", "type": "message", "role": "assistant",
                            "status": "completed", "content": [{"type": "output_text",
                            "text": "offline-ok", "annotations": []}]}]
                    })

                options = {"api_key": "offline-placeholder"} if auth == "bearer" else {
                    "api_key": None, "access_key_id": "offline-access-key", "secret_access_key": "offline-secret"}
                transport = httpx2.MockTransport(respond)
                with httpx2.Client(transport=transport) as http:
                    with OpenAI(provider=bedrock(region="us-east-1", endpoint=endpoint, **options), http_client=http, max_retries=0) as client:
                        response = client.responses.create(model=model, input="Local fictional SDK check")
                        require(response.output_text == "offline-ok" and len(intercepted) == 1)
                checks.append({"endpoint": endpoint, "auth": auth, "status": "PASS", "in_memory_requests": 1})
    return {"offline": True, "openai_python": importlib.metadata.version("openai"),
            "checks": checks, "network_requests": 0, "live_aws_access": "NOT_VERIFIED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan", type=Path)
    group.add_argument("--probe-sdk", action="store_true")
    args = parser.parse_args()
    try:
        result = probe_sdk() if args.probe_sdk else check_plan(load_plan(args.plan))
        print(json.dumps(result, indent=2))
        return 1 if result.get("issues") else 0
    except Exception:
        # Do not echo an exception or supplied values: these can contain private
        # profile names, file paths, or accidentally pasted credential material.
        print(json.dumps({"status": "ERROR", "reason": "INVALID_PLAN_OR_FAILED_OFFLINE_SDK_CHECK",
                          "network_requests": 0, "ready_for_live_work": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
