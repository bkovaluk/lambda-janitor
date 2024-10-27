# tests/test_janitor.py

import os
from datetime import datetime, timedelta
from unittest import mock

import boto3
import pytest
from moto import mock_lambda, mock_cloudwatch, mock_ses

from lambda_janitor.main import lambda_handler

# Constants for test configuration
RETENTION_DAYS = 30
ALERT_DAYS = 7
MOCK_EMAIL_SENDER = "notify@example.com"
MOCK_EMAIL_RECIPIENTS = "user@example.com,admin@example.com"

@pytest.fixture
def lambda_env_variables():
    """Set up environment variables for testing."""
    with mock.patch.dict(os.environ, {
        "RETENTION_DAYS": str(RETENTION_DAYS),
        "ALERT_DAYS": str(ALERT_DAYS),
        "EMAIL_SENDER": MOCK_EMAIL_SENDER,
        "EMAIL_RECIPIENTS": MOCK_EMAIL_RECIPIENTS,
    }):
        yield

@pytest.fixture
def aws_mocks():
    """Set up Moto mocks for Lambda, CloudWatch, and SES."""
    with mock_lambda(), mock_cloudwatch(), mock_ses():
        yield

def create_mock_lambda_versions(lambda_client, function_name, num_versions, retention_days):
    """
    Create mock Lambda versions for testing.
    """
    # Create a Lambda function
    lambda_client.create_function(
        FunctionName=function_name,
        Runtime="python3.8",
        Role="arn:aws:iam::123456789012:role/service-role/test-role",
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": b"def handler(event, context): pass"},
    )

    # Add multiple versions
    for i in range(1, num_versions + 1):
        # Publish a new version with a last modified date in the past
        lambda_client.publish_version(FunctionName=function_name)
        version_info = lambda_client.get_function(FunctionName=function_name, Qualifier=str(i))
        last_modified = (datetime.now() - timedelta(days=retention_days + i)).strftime('%Y-%m-%dT%H:%M:%S.%f%z')
        version_info["Configuration"]["LastModified"] = last_modified

def test_lambda_cleanup(lambda_env_variables, aws_mocks):
    """
    Test the Lambda cleanup function.
    """
    # Initialize mock clients
    lambda_client = boto3.client("lambda")
    ses_client = boto3.client("ses")
    cloudwatch_client = boto3.client("cloudwatch")

    # Create mock Lambda function and versions
    function_name = "test_lambda_function"
    num_versions = 5
    create_mock_lambda_versions(lambda_client, function_name, num_versions, RETENTION_DAYS)

    # Set up SES email configuration
    ses_client.verify_email_identity(EmailAddress=MOCK_EMAIL_SENDER)
    for email in MOCK_EMAIL_RECIPIENTS.split(","):
        ses_client.verify_email_identity(EmailAddress=email.strip())

    # Mock invocation data in CloudWatch for some versions
    for i in range(1, num_versions + 1):
        # Mock CloudWatch invocations metric for some versions
        if i % 2 == 0:  # Only odd-numbered versions should be deleted
            cloudwatch_client.put_metric_data(
                Namespace="AWS/Lambda",
                MetricData=[
                    {
                        "MetricName": "Invocations",
                        "Dimensions": [
                            {"Name": "FunctionName", "Value": function_name},
                            {"Name": "Resource", "Value": f"{function_name}:{i}"}
                        ],
                        "Timestamp": datetime.now() - timedelta(days=RETENTION_DAYS - 1),
                        "Value": 1.0,
                        "Unit": "Count"
                    }
                ]
            )

    # Run the cleanup handler
    lambda_handler({}, {})

    # Check that odd-numbered versions are deleted
    for i in range(1, num_versions + 1, 2):  # Odd-numbered versions should be deleted
        with pytest.raises(lambda_client.exceptions.ResourceNotFoundException):
            lambda_client.get_function(FunctionName=function_name, Qualifier=str(i))

    # Check SES for sent email
    sent_emails = ses_client.list_identities()
    assert MOCK_EMAIL_SENDER in sent_emails["Identities"]

