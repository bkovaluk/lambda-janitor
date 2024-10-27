# Lambda Janitor

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A Python package that automates the cleanup of old, unused AWS Lambda versions. This package identifies Lambda versions that haven’t been invoked in a specified number of days, deletes them, and sends notifications about upcoming deletions via AWS SES.

## Features

- **Automated Cleanup**: Deletes unused Lambda function versions based on a configurable retention period.
- **Notifications via SES**: Sends alert emails for Lambda versions nearing their cleanup date.
- **Configurable**: Easily adjust retention days, alert days, and email recipients via environment variables.
- **Detailed Logging**: Provides structured and enhanced logging for easy monitoring in CloudWatch.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Development](#development)
- [License](#license)

## Installation

### Clone the Repository

~~~bash
git clone https://github.com/yourusername/lambda-janitor.git
cd lambda-janitor
~~~

### Install Dependencies

Install runtime dependencies:

~~~bash
uv install
~~~

Install development dependencies (e.g., for testing):

~~~bash
uv install --dev
~~~

## Usage

This package is designed to be deployed as an AWS Lambda function, but you can test it locally.

### Running the Cleanup Script

~~~bash
uv run lambda_janitor/main.py
~~~

### Running Tests

~~~bash
uv run test
~~~

## Configuration

Configure the following environment variables in your Lambda console or locally in your `.env` file for testing.

| Variable         | Description                                                                                          | Default | Example                 |
|------------------|------------------------------------------------------------------------------------------------------|---------|-------------------------|
| `RETENTION_DAYS` | Number of days after which unused Lambda versions are marked for deletion.                           | `30`    | `RETENTION_DAYS=30`     |
| `ALERT_DAYS`     | Number of days before deletion to send a notification email.                                         | `7`     | `ALERT_DAYS=7`          |
| `EMAIL_RECIPIENTS` | Comma-separated list of email addresses to receive notifications.                                   | None    | `EMAIL_RECIPIENTS=user@example.com,admin@example.com` |
| `EMAIL_SENDER`   | The email address to send notifications from (must be verified in AWS SES).                          | None    | `EMAIL_SENDER=notify@example.com` |

### Example Configuration

~~~bash
export RETENTION_DAYS=30
export ALERT_DAYS=7
export EMAIL_RECIPIENTS="user@example.com,admin@example.com"
export EMAIL_SENDER="notify@example.com"
~~~

## Development

### Project Structure

~~~plaintext
lambda_janitor/
├── lambda_janitor/
│   └── main.py
│   └── __init__.py
├── tests/
│   └── test_janitor.py
├── pyproject.toml
└── README.md
~~~

- **`lambda_janitor/main.py`**: Contains the main logic for identifying, deleting, and notifying about unused Lambda versions.
- **`tests/test_janitor.py`**: Test cases for unit testing the cleanup functionality.

### Adding New Dependencies

To add new runtime dependencies:

~~~bash
uv add <package-name>
~~~

To add new dev dependencies:

~~~bash
uv add <package-name> --dev
~~~

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

*Happy Cleaning!*

