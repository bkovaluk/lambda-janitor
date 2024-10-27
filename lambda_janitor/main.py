#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: lambda_cleanup.py
Description: This Lambda function automatically cleans up unused Lambda versions older than a specified retention period.
             It sends a notification email for Lambda versions approaching cleanup and those that have been deleted.

Environment Variables:
    - RETENTION_DAYS: Number of days after which unused Lambda versions are marked for deletion (default: 30).
    - ALERT_DAYS: Number of days before deletion to send a notification email (default: 7).
    - EMAIL_RECIPIENTS: Comma-separated list of email addresses to receive notifications.
    - EMAIL_SENDER: The email address to send notifications from (must be verified in SES).

Requirements:
    - boto3

Usage:
    This Lambda function is meant to be triggered on a scheduled basis (e.g., daily) via Amazon CloudWatch Events or EventBridge.
"""

__author__ = "Bradley Kovaluk"
__version__ = "1.0"
__date__ = "2024-10-25"

import boto3
import os
import logging
from datetime import datetime, timedelta

# Initialize clients for Lambda, CloudWatch, and SES
lambda_client = boto3.client("lambda")
cloudwatch_client = boto3.client("cloudwatch")
ses_client = boto3.client("ses")

# Environment variables for configuration
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))
ALERT_DAYS = int(os.getenv("ALERT_DAYS", "7"))
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "").split(",")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    Main handler for the Lambda cleanup function.
    """
    logger.info("Starting Lambda cleanup process")
    logger.info(f"Retention period set to {RETENTION_DAYS} days; alert threshold set to {ALERT_DAYS} days")

    try:
        cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
        alert_date = datetime.now() - timedelta(days=(RETENTION_DAYS - ALERT_DAYS))

        alert_versions = []
        deleted_versions = []

        paginator = lambda_client.get_paginator("list_functions")
        function_pages = paginator.paginate()

        for page in function_pages:
            for function in page["Functions"]:
                function_name = function["FunctionName"]
                logger.info(f"Processing function: {function_name}")

                version_paginator = lambda_client.get_paginator("list_versions_by_function")
                version_pages = version_paginator.paginate(FunctionName=function_name)

                for version_page in version_pages:
                    for version in version_page["Versions"]:
                        if version["Version"] == "$LATEST":
                            continue

                        last_modified = datetime.strptime(version["LastModified"], '%Y-%m-%dT%H:%M:%S.%f%z')
                        logger.debug(f"Evaluating version {version['Version']} (Last Modified: {last_modified})")

                        if last_modified > cutoff_date:
                            if last_modified <= alert_date:
                                logger.info(f"Version {version['Version']} of {function_name} approaching cleanup date")
                                alert_versions.append((function_name, version["Version"], last_modified))
                            continue

                        invocation_count = get_invocation_count(function_name, version["Version"], cutoff_date)
                        if invocation_count > 0:
                            logger.info(f"Skipping version {version['Version']} of {function_name}; Invoked {invocation_count} times within retention period")
                            continue

                        logger.warning(f"Deleting version {version['Version']} of function {function_name}")
                        deleted_versions.append((function_name, version["Version"], last_modified))
                        delete_lambda_version(function_name, version["Version"])

        if alert_versions or deleted_versions:
            send_cleanup_alert(alert_versions, deleted_versions)

        logger.info("Lambda cleanup process completed successfully")

    except Exception as e:
        logger.error(f"Error during Lambda cleanup: {e}", exc_info=True)
        raise

def get_invocation_count(function_name, version, cutoff_date):
    """
    Retrieves the invocation count of a Lambda version since the cutoff date.
    """
    try:
        response = cloudwatch_client.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Invocations",
            Dimensions=[
                {"Name": "FunctionName", "Value": function_name},
                {"Name": "Resource", "Value": f"{function_name}:{version}"}
            ],
            StartTime=cutoff_date,
            EndTime=datetime.now(),
            Period=86400,  # 1 day
            Statistics=["Sum"],
        )
        count = sum(dp["Sum"] for dp in response["Datapoints"])
        logger.debug(f"Invocation count for {function_name}:{version} is {count}")
        return count
    except Exception as e:
        logger.error(f"Error retrieving invocation count for {function_name}:{version}: {e}", exc_info=True)
        return 0

def delete_lambda_version(function_name, version):
    """
    Deletes a specific version of a Lambda function.
    """
    try:
        lambda_client.delete_function(FunctionName=function_name, Qualifier=version)
        logger.info(f"Deleted version {version} of function {function_name}")
    except Exception as e:
        logger.error(f"Failed to delete version {version} of function {function_name}: {e}", exc_info=True)

def send_cleanup_alert(alert_versions, deleted_versions):
    """
    Sends an email notification for Lambda versions nearing deletion and those that have been deleted.
    """
    if not EMAIL_RECIPIENTS or not EMAIL_SENDER:
        logger.error("Missing EMAIL_RECIPIENTS or EMAIL_SENDER environment variable. Skipping email alert.")
        return

    message_body = "<html><body><h2>Lambda Cleanup Notification</h2>"

    if deleted_versions:
        message_body += "<h3>Deleted Lambda Versions</h3><table border='1' cellpadding='5' cellspacing='0'>"
        message_body += "<tr><th>Function Name</th><th>Version</th><th>Last Modified</th></tr>"
        for function_name, version, last_modified in deleted_versions:
            message_body += f"<tr><td>{function_name}</td><td>{version}</td><td>{last_modified.strftime('%Y-%m-%d')}</td></tr>"
        message_body += "</table><br>"

    if alert_versions:
        message_body += "<h3>Lambda Versions Scheduled for Deletion Soon</h3><table border='1' cellpadding='5' cellspacing='0'>"
        message_body += "<tr><th>Function Name</th><th>Version</th><th>Last Modified</th></tr>"
        for function_name, version, last_modified in alert_versions:
            message_body += f"<tr><td>{function_name}</td><td>{version}</td><td>{last_modified.strftime('%Y-%m-%d')}</td></tr>"
        message_body += "</table><br>"

    message_body += "</body></html>"

    try:
        response = ses_client.send_email(
            Source=EMAIL_SENDER,
            Destination={"ToAddresses": EMAIL_RECIPIENTS},
            Message={
                "Subject": {"Data": "Lambda Cleanup Notification"},
                "Body": {"Html": {"Data": message_body}}
            }
        )
        logger.info("Alert email sent successfully to %s", ", ".join(EMAIL_RECIPIENTS))
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}", exc_info=True)

