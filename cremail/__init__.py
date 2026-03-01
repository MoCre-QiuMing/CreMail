"""
CreMail - A powerful and easy-to-use Python email sending module

This package provides a comprehensive solution for sending emails with
support for various configuration methods, attachments, async sending,
and verification code generation.

For more information, please check the documentation at:
https://github.com/MoCre-QiuMing/CreMail
"""

from .CreMail import (
    CreMail,
    SendResult,
    ConfigProvider,
    JSONConfigProvider,
    DatabaseConfigProvider,
    RemoteConfigProvider,
    SMTPClient,
    AioSMTPLibClient,
    SMTPLibClient,
    EmailSendError,
    ConfigError,
    SMTPConnectionError,
    AttachmentError,
    SizeLimitError,
    RateLimitError,
    ContentValidationError,
    EmailContent,
    EmailAttachment,
    VERIFICATION_CODE_DIGITS,
    VERIFICATION_CODE_LETTERS,
    VERIFICATION_CODE_MIX,
    send_email_with_config,
    async_send_email,
    render_template,
    generate_verification_code,
    generate_alphanumeric_verification_code,
    generate_letters_verification_code,
    generate_verification_code_unified,
    get_default_sender,
    send_email_with_default_sender,
    get_password_securely
)

__version__ = "1.2.1"
__author__ = "Your Name"
__license__ = "MIT"
__all__ = [
    'CreMail',
    'SendResult',
    'ConfigProvider',
    'JSONConfigProvider',
    'DatabaseConfigProvider',
    'RemoteConfigProvider',
    'SMTPClient',
    'AioSMTPLibClient',
    'SMTPLibClient',
    'EmailSendError',
    'ConfigError',
    'SMTPConnectionError',
    'AttachmentError',
    'SizeLimitError',
    'RateLimitError',
    'ContentValidationError',
    'EmailContent',
    'EmailAttachment',
    'VERIFICATION_CODE_DIGITS',
    'VERIFICATION_CODE_LETTERS',
    'VERIFICATION_CODE_MIX',
    'send_email_with_config',
    'async_send_email',
    'render_template',
    'generate_verification_code',
    'generate_alphanumeric_verification_code',
    'generate_letters_verification_code',
    'generate_verification_code_unified',
    'get_default_sender',
    'send_email_with_default_sender',
    'get_password_securely'
]