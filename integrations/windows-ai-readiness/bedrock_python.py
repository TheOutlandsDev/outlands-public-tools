"""Offline readiness check or explicit live OpenAI-on-Bedrock request."""
import argparse
import importlib.metadata
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--live", action="store_true")
    args = parser.parse_args()

    from openai import OpenAI
    from openai.providers import bedrock

    if args.check:
        print(f"READY openai-python {importlib.metadata.version('openai')}; no AWS request")
        return
    key = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
    if not key:
        parser.error("AWS_BEARER_TOKEN_BEDROCK is required for --live")
    client = OpenAI(provider=bedrock(region="us-east-1", api_key=key))
    response = client.responses.create(
        model="openai.gpt-6-sol",
        input="Reply with one sentence describing an offline development check.",
    )
    print(response.output_text)


if __name__ == "__main__":
    main()
