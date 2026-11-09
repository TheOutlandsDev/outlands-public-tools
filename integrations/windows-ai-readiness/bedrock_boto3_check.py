"""Check the AWS Bedrock Runtime SDK service model without contacting AWS."""
import importlib.metadata

import boto3


def main():
    session = boto3.Session(
        aws_access_key_id="offline-placeholder",
        aws_secret_access_key="offline-placeholder",
        region_name="us-east-1",
    )
    client = session.client("bedrock-runtime")
    assert client.meta.service_model.operation_model("Converse").name == "Converse"
    print(f"READY boto3 {importlib.metadata.version('boto3')} Bedrock Runtime model; no AWS request")


if __name__ == "__main__":
    main()
