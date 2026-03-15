# CreMail Email Sending Module

<div align="center">

[![English](README.md)](README.md) | [![中文](CreMail_zh.md)](CreMail_zh.md)

[![Python](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[
**A powerful and easy-to-use Python email sending module**

✨ Multiple configuration methods  
🔧 Synchronous and asynchronous support  
🚀 High-performance batch sending  
📧 HTML and plain text support  
🔒 Secure password management  
🎯 Smart retry and error handling  

</div>

## 📋 Table of Contents

- [Features](#-features)
- [Comparison with Other Email Modules](#-comparison-with-other-email-modules)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Reference](#-api-reference)
- [Examples](#-examples)
- [License](#-license)

## ✨ Features

- **Modular Design**: Uses ConfigProvider protocol, supports JSON, database, remote, and other configuration sources
- **High-Performance Concurrency**: Supports asynchronous sending and batch sending with built-in semaphore for concurrency control
- **Smart Retry**: Supports exponential backoff and total timeout control to avoid infinite retries
- **Secure Password Management**: Supports password callback functions to avoid hardcoding passwords in code
- **Flexible Content**: Supports sending any HTML/plain text email content, supports multi-format content
- **Multiple Interfaces**: Class-based and function-based APIs for different use cases
- **Configurable**: Supports configuration files, environment variables, dictionary parameters, and more
- **Verification Code Generation**: Provides numeric, alphanumeric, and letters-only verification code generation
- **Attachment Support**: Supports sending emails with attachments, automatically checks size limits
- **Exception Hierarchy**: Defines detailed exception classes for precise error handling
- **SMTP Abstraction**: Supports SMTPClient protocol for easier testing and extension
- **Display Names**: Supports sender and recipient display names
- **Email Validation**: Validates email formats before sending, prevents invalid addresses
- **Priority Support**: Supports email priority settings
- **Global Instance**: Provides default instance, reducing repetitive configuration

## 📊 Comparison with Other Email Modules

| Feature | CreMail | smtplib | yagmail | aiosmtplib |
|---------|---------|---------|---------|------------|
| Configuration Management | ✅ Advanced | ❌ Basic | ✅ Medium | ❌ None |
| Async Support | ✅ Complete | ❌ Sync Only | ❌ Sync Only | ✅ Complete |
| Batch Sending | ✅ High-Performance | ❌ None | ❌ None | ❌ None |
| Smart Retry | ✅ Advanced | ❌ None | ❌ Basic | ❌ None |
| Concurrency Control | ✅ Advanced | ❌ None | ❌ None | ❌ None |
| Password Security | ✅ Advanced | ❌ Basic | ❌ Basic | ❌ Basic |
| Verification Code Gen | ✅ Built-in | ❌ None | ❌ None | ❌ None |
| Modular Design | ✅ Advanced | ❌ Low | ❌ Medium | ❌ Low |
| Display Names | ✅ Supported | ✅ Supported | ✅ Supported | ❌ None |
| Email Validation | ✅ Pre-send Validation | ❌ Send-time validation | ❌ Send-time validation | ❌ Send-time validation |

CreMail excels in functionality, security, and usability compared to other modules, especially suitable for scenarios requiring high performance and security.

## 🚀 Installation

1. Install directly from GitHub:
   ```bash
   pip install git+https://github.com/MoCre-QiuMing/CreMail.git
   ```
   
2. Or clone or download this repository and copy `cremail.py` to your project directory

## ⚙️ Configuration

Create `email_config.json` file in your project root directory with the following format:

```json
{
  "smtp_server": "smtp.example.com",
  "smtp_port": 587,
  "email": "your_email@example.com",
  "password": "your_password_or_token"
}
```

### Common Email Provider SMTP Settings:

| Provider | SMTP Server | Port | SSL |
|----------|-------------|------|-----|
| QQ Mail | smtp.qq.com | 587 | Yes |
| Gmail | smtp.gmail.com | 587 | Yes |
| 163 Mail | smtp.163.com | 587 | Yes |
| Outlook | smtp-mail.outlook.com | 587 | Yes |

> **Note**: For QQ Mail, the "password" field should contain an "authorization code" instead of your email password. You can obtain this from QQ Mail settings.

## 📖 Usage

### Method 1: Using CreMail Class

```python
from cremail import CreMail

# Initialize with configuration file (default: email_config.json)
sender = CreMail()

# Or initialize with direct parameters
sender = CreMail(
    smtp_server="smtp.qq.com",
    smtp_port=587,
    email="your_email@qq.com",
    password="your_authorization_code"
)

# Send custom email
success = sender.send_email(
    "user@example.com",
    "Custom Subject",
    "<h1>Hello!</h1><p>This is a custom HTML email.</p>",
    "html"
)

# Send verification code email (using verification code generation functions)
from cremail import generate_verification_code
verification_code = generate_verification_code()
verification_content = f"Your verification code is: <strong>{verification_code}</strong>, please use it within 5 minutes."
success = sender.send_email(
    "user@example.com",
    "Verification",
    verification_content,
    "html"
)
```

### Method 2: Using Regular Functions

```python
from cremail import send_email_with_config

# Send custom email
success = send_email_with_config(
    "user@example.com",
    "Subject",
    "<h1>Custom content</h1>",
    "email_config.json",
    "html"
)
```

### Method 3: Using Verification Code Generation Functions

```python
from cremail import CreMail, generate_verification_code, generate_alphanumeric_verification_code, generate_letters_verification_code, generate_verification_code_unified

sender = CreMail()

# Generate 6-digit numeric verification code
numeric_code = generate_verification_code(6)

# Generate 8-character alphanumeric verification code
alphanumeric_code = generate_alphanumeric_verification_code(8)

# Generate 4-letter verification code
letters_code = generate_letters_verification_code(4)

# Use unified API to generate different types of verification codes
unified_digits_code = generate_verification_code_unified(6, mode='digits')
unified_letters_code = generate_verification_code_unified(8, mode='letters')
unified_mix_code = generate_verification_code_unified(6, mode='mix')

# Create email content with different verification code types
numeric_content = f"Your numeric verification code is: <strong>{numeric_code}</strong>, please use it within 5 minutes."
alphanumeric_content = f"Your alphanumeric verification code is: <strong>{alphanumeric_code}</strong>, please use it within 5 minutes."
letters_content = f"Your letters verification code is: <strong>{letters_code}</strong>, please use it within 5 minutes."

# Send emails with different types of verification codes
success1 = sender.send_email(
    "user1@example.com",
    "Numeric Verification",
    numeric_content,
    "html"
)

success2 = sender.send_email(
    "user2@example.com",
    "Alphanumeric Verification",
    alphanumeric_content,
    "html"
)

success3 = sender.send_email(
    "user3@example.com",
    "Letters Verification",
    letters_content,
    "html"
)
```

### Method 4: Sending Emails with Attachments

```python
from cremail import CreMail

sender = CreMail()

# Send email with attachments
success = sender.send_email(
    "user@example.com",
    "Email with Attachments",
    "Please check the files in the attachments.",
    "plain",
    attachments=["path/to/file1.pdf", "path/to/file2.jpg"]  # List of attachment file paths
)

# Send email with attachments but ignore attachment errors (continue sending even if some attachments don't exist)
success = sender.send_email(
    "user@example.com",
    "Email with Attachments",
    "Please check the files in the attachments.",
    "plain",
    attachments=["path/to/file1.pdf", "path/to/file2.jpg", "path/to/missing_file.pdf"],
    ignore_attachment_errors=True  # Ignore attachment errors and continue sending the email
)

# You can also send emails with attachments using function approach
from cremail import send_email_with_config

success = send_email_with_config(
    "user@example.com",
    "Email with Attachments",
    "Please check the files in the attachments.",
    "email_config.json",
    "plain",
    attachments=["path/to/file1.pdf", "path/to/file2.jpg"]
)

# Send email with function approach and ignore attachment errors
success = send_email_with_config(
    "user@example.com",
    "Email with Attachments",
    "Please check the files in the attachments.",
    "email_config.json",
    "plain",
    attachments=["path/to/file1.pdf", "path/to/missing_file.pdf"],
    ignore_attachment_errors=True
)
```

### Method 5: Configuring Logging

```python
import logging
from cremail import CreMail

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('cremail')
logger.setLevel(logging.INFO)

# Or add custom handlers
handler = logging.FileHandler('cremail.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

sender = CreMail()
result = sender.send_email(
    "user@example.com",
    "Test Email",
    "This is a test email.",
    "plain"
)
print(f"Send result: {result.success}, Details: {result.error_detail}")
```

### Method 6: Using Environment Variables Configuration

```python
import os
from cremail import CreMail

# Set environment variables
os.environ['SMTP_SERVER'] = 'smtp.example.com'
os.environ['SMTP_PORT'] = '587'
os.environ['SMTP_EMAIL'] = 'your_email@example.com'
os.environ['SMTP_PASSWORD'] = 'your_password_or_token'

# Initialize with environment variables
sender = CreMail()
result = sender.send_email(
    "user@example.com",
    "Environment Variables Config Email",
    "This is an email sent with environment variable configuration.",
    "html"
)
```

### Method 7: Using Configuration Dictionary

```python
from cremail import CreMail

# Use configuration dictionary
config = {
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "email": "your_email@example.com",
    "password": "your_password_or_token"
}

sender = CreMail(config_dict=config)
result = sender.send_email(
    "user@example.com",
    "Config Dictionary Email",
    "This is an email sent using configuration dictionary.",
    "html"
)
```

### Method 8: Exception Handling

```python
from cremail import CreMail, ConfigError, EmailSendError

try:
    sender = CreMail()
    result = sender.send_email(
        "user@example.com",
        "Exception Handling Test",
        "This is an email to test exception handling.",
        "html"
    )
    
    if not result.success:
        print(f"Send failed: {result.error_detail}")
    else:
        print(f"Send successful, message ID: {result.message_id}")
        
except ConfigError as e:
    print(f"Configuration error: {e}")
except EmailSendError as e:
    print(f"Email sending error: {e}")
except Exception as e:
    print(f"Other error: {e}")
```

### Method 9: Using Retry Mechanism

```python
from cremail import CreMail

sender = CreMail()
# Set maximum retry count to 3
result = sender.send_email(
    "user@example.com",
    "Email with Retry Mechanism",
    "This is an email sent with retry mechanism.",
    "html",
    max_retries=3
)
```

### Method 10: Using Asynchronous Sending

```python
import asyncio
from cremail import async_send_email

async def send_async_email():
    result = await async_send_email(
        "user@example.com",
        "Asynchronous Email",
        "This is an asynchronously sent email.",
        smtp_server="smtp.qq.com",
        smtp_port=587,
        email="your_email@qq.com",
        password="your_authorization_code"
    )
    print(f"Asynchronous send result: {result.success}")

# Run asynchronous function
asyncio.run(send_async_email())
```

### Method 11: Using Batch Sending

```python
import asyncio
from cremail import CreMail

async def batch_send_example():
    sender = CreMail()
    
    emails = [
        {
            "recipient_email": "user1@example.com",
            "subject": "Batch Email 1",
            "content": "This is the first email sent in batch",
            "content_type": "plain"
        },
        {
            "recipient_email": "user2@example.com",
            "subject": "Batch Email 2",
            "content": "This is the second email sent in batch",
            "content_type": "plain"
        }
    ]
    
    results = await sender.batch_send(emails, batch_size=5, max_concurrent=3)
    for i, result in enumerate(results):
        print(f"Email {i+1} send result: {result.success}")

# Run asynchronous function
asyncio.run(batch_send_example())
```

## 📚 API Reference

### Class: CreMail

#### `__init__(self, smtp_server=None, smtp_port=None, email=None, password=None, config_file="email_config.json", config_dict=None, config_provider=None, max_attachment_size=10485760, timeout=30, use_tls=True, use_ssl=False, provider_priority=False, from_display_name=None, smtp_client=None, password_callback=None, log_file=None)`

Initialize email sender.

**Parameters:**
- `smtp_server` (str, optional): SMTP server address
- `smtp_port` (int, optional): SMTP server port
- `email` (str, optional): Sender email address
- `password` (str, optional): Sender email password or authorization code
- `config_file` (str): Configuration file path (default: "email_config.json")
- `config_dict` (dict, optional): Configuration dictionary
- `config_provider` (ConfigProvider, optional): Configuration provider
- `max_attachment_size` (int): Maximum attachment size (default: 10MB)
- `timeout` (int): Connection timeout (default: 30 seconds)
- `use_tls` (bool): Whether to use TLS (default: True)
- `use_ssl` (bool): Whether to use SSL (default: False)
- `provider_priority` (bool): Whether to prioritize config_provider (default: False)
- `from_display_name` (str, optional): Sender display name
- `smtp_client` (SMTPClient, optional): SMTP client implementation
- `password_callback` (callable, optional): Password retrieval callback function
- `log_file` (str, optional): Log file path for writing logs to file. Can be absolute path or relative path (relative to current working directory). Default: None, logs to console only

#### `send_email(self, recipient_email: Union[str, List[str]], subject: str, content: Union[str, dict], content_type: str = "html", attachments: List[str] = None, ignore_attachment_errors: bool = False, max_retries: int = 2, cc_recipients: List[str] = None, bcc_recipients: List[str] = None, reply_to: str = None, priority: Literal["high", "normal", "low"] = "normal", total_timeout: float = None) -> SendResult`

Send custom email with specified content.

**Parameters:**
- `recipient_email` (Union[str, List[str]]): Recipient email address or address list
- `subject` (str): Email subject
- `content` (Union[str, dict]): Email content (string or dictionary with 'html' and 'text' keys)
- `content_type` (str): Content type - "html" or "plain" (default: "html")
- `attachments` (List[str], optional): List of attachment file paths
- `ignore_attachment_errors` (bool, optional): Whether to ignore attachment errors and continue sending (default: False)
- `max_retries` (int, optional): Maximum retry count (default: 2)
- `cc_recipients` (List[str], optional): CC recipients list
- `bcc_recipients` (List[str], optional): BCC recipients list
- `reply_to` (str, optional): Reply-to address
- `priority` (Literal["high", "normal", "low"]): Email priority (default: "normal")
- `total_timeout` (float, optional): Total timeout

**Returns:**
- `SendResult`: Object containing send result

### Regular Functions

#### `send_email_with_config(recipient_email, subject, content, config_file="email_config.json", content_type="html", attachments: List[str] = None, ignore_attachment_errors: bool = False, max_retries: int = 2, cc_recipients: List[str] = None, bcc_recipients: List[str] = None, reply_to: str = None, priority: Literal["high", "normal", "low"] = "normal", password_callback=None) -> SendResult`

Regular function to send email with configuration file.

#### `async_send_email(recipient_email, subject, content, smtp_server=None, smtp_port=None, email=None, password=None, config_file="email_config.json", config_dict=None, content_type="html", attachments: List[str] = None, ignore_attachment_errors: bool = False, max_retries: int = 2, max_attachment_size: int = 10485760, total_timeout: float = None, cc_recipients: List[str] = None, bcc_recipients: List[str] = None, reply_to: str = None, priority: Literal["high", "normal", "low"] = "normal", from_display_name: str = None) -> SendResult`

Asynchronous function to send email (requires aiosmtplib library).

Configuration priority: Direct parameters > config_dict > Environment variables > Configuration file

#### `render_template(template_file, data) -> str`

Render email templates using Jinja2 (requires jinja2 library).

#### `generate_verification_code(length: int = 6) -> str`

Generate numeric verification code with specified length (using secrets module for enhanced security), can be used in email content.

#### `generate_alphanumeric_verification_code(length: int = 6) -> str`

Generate alphanumeric verification code with specified length (using secrets module for enhanced security), can be used in email content.

#### `generate_letters_verification_code(length: int = 6) -> str`

Generate letters-only verification code with specified length (using secrets module for enhanced security), can be used in email content.

#### `generate_verification_code_unified(length: int = 6, mode: str = 'digits') -> str`

Unified verification code generation function, select verification code type via mode parameter.

**Parameters:**
- `length` (int): Verification code length
- `mode` (str): Verification code type, 'digits' for numeric, 'letters' for letters, 'mix' for alphanumeric

**Returns:**
- `str`: Generated verification code string

### Custom Exception Classes

The module defines a detailed exception hierarchy:

- `EmailSendError`: Base class for email sending errors
- `ConfigError`: Configuration error
- `SMTPConnectionError`: SMTP connection error
- `AttachmentError`: Attachment handling error
- `SizeLimitError`: Attachment size limit error
- `RateLimitError`: Send rate limit error
- `ContentValidationError`: Content validation error

### SendResult Class

Returns SendResult object after sending email, containing the following attributes:

- `success` (bool): Whether sending was successful
- `message_id` (str): Email message ID
- `error_detail` (str): Error details
- `accepted_recipients` (list): List of accepted recipients
- `timestamp` (float): Send timestamp
- `exception` (Exception): Original exception object

### Configuration Methods

Supports multiple configuration methods with the following priority:
1. Direct parameters
2. config_dict
3. Environment variables
4. Configuration file

Environment variable names:
- `SMTP_SERVER`: SMTP server address
- `SMTP_PORT`: SMTP server port
- `SMTP_EMAIL`: Sender email
- `SMTP_PASSWORD`: Sender password or authorization code

### Retry Mechanism

The send_email method supports the max_retries parameter with a default of 2 retries, using exponential backoff algorithm with random jitter.

### Asynchronous Support

Provides async_send_email asynchronous function and batch_send batch sending feature, requires aiosmtplib library.

### Template Rendering

Provides render_template function, requires jinja2 library.

### Logging

The module provides flexible logging options with user-friendly error messages that include troubleshooting suggestions. Main log events include:

- `INFO`: Email sent successfully
- `WARNING`: Configuration file does not exist
- `ERROR`: Configuration file format error, email sending failure, attachment handling errors, etc.

You can configure logging in two ways:

1. Using the `log_file` parameter in CreMail initialization to write logs to a file:
```python
from cremail import CreMail

# Write logs to a file
sender = CreMail(log_file='cremail.log')
result = sender.send_email(
    "user@example.com",
    "Test Email",
    "This is a test email.",
    "plain"
)
```

2. Using standard Python logging module (traditional approach):
```python
import logging
from cremail import CreMail

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('cremail')
logger.setLevel(logging.INFO)

# Or add custom handlers
handler = logging.FileHandler('cremail.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

sender = CreMail()
result = sender.send_email(
    "user@example.com",
    "Test Email",
    "This is a test email.",
    "plain"
)
```

The improved logging system now provides clear, actionable error messages with troubleshooting tips to help users quickly identify and resolve common issues such as:
- SMTP connection errors (check server address and port)
- Authentication errors (verify email and password/authorization code)
- Recipient errors (verify email addresses)
- Attachment errors (check file paths and sizes)
- Configuration errors (verify file format and permissions)

## 💡 Examples

### Example 1: Sending Welcome Email

```python
from cremail import CreMail

sender = CreMail()
success = sender.send_email(
    "newuser@example.com",
    "Welcome to Our Service!",
    """
    <html>
    <body>
        <h2>Welcome!</h2>
        <p>Thank you for joining our service.</p>
        <p>We're glad to have you!</p>
    </body>
    </html>
    """,
    "html"
)
```

### Example 2: Sending Notification Email

```python
from cremail import send_email_with_config

success = send_email_with_config(
    "user@example.com",
    "System Notification",
    "<p>Your order has been successfully submitted, we will process it as soon as possible.</p>",
    "email_config.json",
    "html"
)
```

### Example 3: Sending Numeric Verification Code Email

```python
from cremail import CreMail, generate_verification_code

sender = CreMail()

# Generate numeric verification code
verification_code = generate_verification_code()

# Create email content with verification code
verification_content = f"""
<html>
<body>
    <h2>Your Verification Code</h2>
    <p>Hello!</p>
    <p>Your verification code is: <strong style="font-size: 32px; color: #00aaff;">{verification_code}</strong></p>
    <p>This verification code will be valid for 10 minutes, please use it promptly.</p>
</body>
</html>
"""

success = sender.send_email(
    "user@example.com",
    "Account Verification",
    verification_content,
    "html"
)
```

### Example 4: Sending Alphanumeric Verification Code Email

```python
from cremail import CreMail, generate_alphanumeric_verification_code

sender = CreMail()

# Generate alphanumeric verification code
verification_code = generate_alphanumeric_verification_code(8)

# Create email content with verification code
verification_content = f"""
<html>
<body>
    <h2>Your Verification Code</h2>
    <p>Hello!</p>
    <p>Your verification code is: <strong style="font-size: 32px; color: #00aaff;">{verification_code}</strong></p>
    <p>This verification code will be valid for 10 minutes, please use it promptly.</p>
</body>
</html>
"""

success = sender.send_email(
    "user@example.com",
    "Account Verification",
    verification_content,
    "html"
)
```

### Example 5: Sending Letters-only Verification Code Email

```python
from cremail import CreMail, generate_letters_verification_code

sender = CreMail()

# Generate letters-only verification code
verification_code = generate_letters_verification_code(6)

# Create email content with verification code
verification_content = f"""
<html>
<body>
    <h2>Your Verification Code</h2>
    <p>Hello!</p>
    <p>Your verification code is: <strong style="font-size: 32px; color: #00aaff;">{verification_code}</strong></p>
    <p>This verification code will be valid for 10 minutes, please use it promptly.</p>
</body>
</html>
"""

success = sender.send_email(
    "user@example.com",
    "Account Verification",
    verification_content,
    "html"
)
```

### Example 6: Sending Plain Text Email

```python
from cremail import CreMail

sender = CreMail()
success = sender.send_email(
    "user@example.com",
    "Plain Text Email",
    "This is a plain text email message.",
    "plain"
)
```

### Example 7: Using HTML and Plain Text Content

```python
from cremail import CreMail

sender = CreMail()
content = {
    "html": "<h1>HTML Content</h1><p>This is HTML content</p>",
    "text": "This is plain text content"
}
success = sender.send_email(
    "user@example.com",
    "Multi-format Email",
    content,
    "html"
)
```

### Example 8: Sending Email with Attachments

```python
from cremail import CreMail

sender = CreMail()

# Send email with attachments
success = sender.send_email(
    "user@example.com",
    "Email with Attachments",
    "Please check the files in the attachments.",
    "plain",
    attachments=["path/to/file1.pdf", "path/to/file2.jpg"]  # List of attachment file paths
)
```

### Example 9: Sending Email with Attachments (Ignore Attachment Errors)

```python
from cremail import CreMail

sender = CreMail()

# Send email with attachments but ignore attachment errors (continue sending even if some attachments don't exist)
success = sender.send_email(
    "user@example.com",
    "Email with Attachments",
    "Please check the files in the attachments.",
    "plain",
    attachments=["path/to/file1.pdf", "path/to/missing_file.pdf"],  # One attachment doesn't exist
    ignore_attachment_errors=True  # Ignore attachment errors and continue sending the email
)
```

### Example 10: Using Unified Verification Code API

```python
from cremail import CreMail, generate_verification_code_unified

sender = CreMail()

# Generate 6-digit numeric verification code
digits_code = generate_verification_code_unified(6, mode='digits')

# Generate 8-letter verification code
letters_code = generate_verification_code_unified(8, mode='letters')

# Generate 6-character alphanumeric verification code
mix_code = generate_verification_code_unified(6, mode='mix')

# Create email content with verification codes
content = f"""
<html>
<body>
    <h2>Your Verification Codes</h2>
    <p>Numeric Verification Code: <strong>{digits_code}</strong></p>
    <p>Letters Verification Code: <strong>{letters_code}</strong></p>
    <p>Alphanumeric Verification Code: <strong>{mix_code}</strong></p>
    <p>Please use within 5 minutes.</p>
</body>
</html>
"""

success = sender.send_email(
    "user@example.com",
    "Multiple Verification Codes",
    content,
    "html"
)
```

### Example 11: Using Asynchronous Sending

```python
import asyncio
from cremail import async_send_email

async def send_verification_email():
    result = await async_send_email(
        "user@example.com",
        "Asynchronous Verification Email",
        "Your verification code is: 123456",
        config_file="email_config.json",
        content_type="plain"
    )
    print(f"Asynchronous send result: {result.success}, Error: {result.error_detail}")

# Run asynchronous function
asyncio.run(send_verification_email())
```

### Example 12: Using Batch Sending

```python
import asyncio
from cremail import CreMail

async def batch_send_emails():
    sender = CreMail()
    
    emails = [
        {
            "recipient_email": "user1@example.com",
            "subject": "Batch Email 1",
            "content": "This is the first email sent in batch",
            "content_type": "plain"
        },
        {
            "recipient_email": "user2@example.com",
            "subject": "Batch Email 2",
            "content": "This is the second email sent in batch",
            "content_type": "plain"
        },
        {
            "recipient_email": "user3@example.com",
            "subject": "Batch Email 3",
            "content": "This is the third email sent in batch",
            "content_type": "plain"
        }
    ]
    
    # Batch send with concurrency limit of 2
    results = await sender.batch_send(emails, batch_size=2, max_concurrent=2)
    
    for i, result in enumerate(results):
        print(f"Email {i+1} send result: {result.success}")
        if not result.success:
            print(f"  Error details: {result.error_detail}")

# Run asynchronous function
asyncio.run(batch_send_emails())
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Feel free to submit Pull Requests. For major changes, please open an issue first to discuss what you would like to change.

## 🐛 Issues

If you encounter any problems or have suggestions for improvements, please open an issue on the GitHub repository.