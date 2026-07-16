import smtplib
import random
import secrets
import string
import json
import logging
import os
import time
import asyncio
import re
import threading
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr, parseaddr
from typing import Optional, Union, List, Dict, Any, Protocol, TypedDict, Literal
from abc import abstractmethod

VERIFICATION_CODE_DIGITS = 'digits'
VERIFICATION_CODE_LETTERS = 'letters'
VERIFICATION_CODE_MIX = 'mix'

try:
    import aiosmtplib
    _HAS_AIOSMTPLIB = True
except ImportError:
    _HAS_AIOSMTPLIB = False

try:
    import jinja2
    _HAS_JINJA2 = True
except ImportError:
    _HAS_JINJA2 = False

_default_sender = None
_default_sender_lock = threading.Lock()

logger = logging.getLogger(__name__)

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

class EmailSendError(Exception):
    def __init__(self, message: str = "邮件发送过程中发生错误"):
        self.message = message
        super().__init__(self.message)

class ConfigError(EmailSendError):
    def __init__(self, message: str = "配置错误"):
        self.message = message
        super().__init__(self.message)

class SMTPConnectionError(EmailSendError):
    def __init__(self, message: str = "SMTP连接错误"):
        self.message = message
        super().__init__(self.message)

class AttachmentError(EmailSendError):
    def __init__(self, message: str = "附件处理错误"):
        self.message = message
        super().__init__(self.message)

class SizeLimitError(EmailSendError):
    pass

class RateLimitError(EmailSendError):
    pass

class ContentValidationError(EmailSendError):
    pass

class ConfigProvider(Protocol):
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        pass

class JSONConfigProvider:
    def __init__(self, file_path: str = "email_config.json"):
        self.file_path = file_path
    def get_config(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {self.file_path} does not exist.")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Config file {self.file_path} format error, please check JSON format.")
            return {}
        except Exception as e:
            logger.error(f"Error reading config file: {str(e)}")
            return {}

class DatabaseConfigProvider:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    def get_config(self) -> Dict[str, Any]:
        logger.warning("Database config provider is not fully implemented yet.")
        return {}

class RemoteConfigProvider:
    def __init__(self, api_endpoint: str):
        self.api_endpoint = api_endpoint
    def get_config(self) -> Dict[str, Any]:
        logger.warning("Remote config provider is not fully implemented yet.")
        return {}

class EmailContent(TypedDict, total=False):
    html: str
    text: str
    subject: Optional[str]

class EmailAttachment(TypedDict):
    path: str
    filename: Optional[str]
    mime_type: Optional[str]

class SMTPClient(Protocol):
    def connect_and_send(self, message, hostname: str, port: int, username: str, password: str, use_tls: bool = True, use_ssl: bool = False, timeout: int = 30, recipients: list = None):
        ...
    async def async_send_message(self, message, hostname: str, port: int, username: str, password: str, start_tls: bool = True, timeout: int = 30, recipients: list = None):
        ...

class AioSMTPLibClient:
    async def async_send_message(self, message, hostname: str, port: int, username: str, password: str, start_tls: bool = True, timeout: int = 30, recipients: list = None):
        if not _HAS_AIOSMTPLIB:
            raise ImportError("aiosmtplib is required for async email sending. Install with: pip install aiosmtplib")
        if recipients:
            return await aiosmtplib.send(
                message,
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                start_tls=start_tls,
                timeout=timeout,
                recipients=recipients
            )
        else:
            to_recipients = [parseaddr(addr.strip())[1] for addr in message['To'].split(',')] if message.get('To') else []
            cc_recipients = [parseaddr(addr.strip())[1] for addr in message.get('Cc', '').split(',')] if message.get('Cc') else []
            all_recipients = to_recipients + cc_recipients
            return await aiosmtplib.send(
                message,
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                start_tls=start_tls,
                timeout=timeout,
                recipients=all_recipients if all_recipients else to_recipients
            )
    def connect_and_send(self, message, hostname: str, port: int, username: str, password: str, use_tls: bool = True, use_ssl: bool = False, timeout: int = 30, recipients: list = None):
        raise NotImplementedError("AioSMTPLibClient does not support synchronous sending. Use SMTPLibClient instead.")

class SMTPLibClient:
    def connect_and_send(self, message, hostname: str, port: int, username: str, password: str, use_tls: bool = True, use_ssl: bool = False, timeout: int = 30, recipients: list = None):
        if use_ssl:
            with smtplib.SMTP_SSL(hostname, port, timeout=timeout) as server:
                if use_tls:
                    # SMTP_SSL already uses SSL, no starttls needed
                    pass
                server.login(username, password)
                text = message.as_string()
                if recipients:
                    result = server.sendmail(username, recipients, text)
                else:
                    to_recipients = [parseaddr(addr.strip())[1] for addr in message['To'].split(',')] if message.get('To') else []
                    cc_recipients = [parseaddr(addr.strip())[1] for addr in message.get('Cc', '').split(',')] if message.get('Cc') else []
                    all_recipients = to_recipients + cc_recipients
                    result = server.sendmail(username, all_recipients if all_recipients else message['To'], text)
                return result
        else:
            with smtplib.SMTP(hostname, port, timeout=timeout) as server:
                if use_tls:
                    server.starttls()
                server.login(username, password)
                text = message.as_string()
                if recipients:
                    result = server.sendmail(username, recipients, text)
                else:
                    to_recipients = [parseaddr(addr.strip())[1] for addr in message['To'].split(',')] if message.get('To') else []
                    cc_recipients = [parseaddr(addr.strip())[1] for addr in message.get('Cc', '').split(',')] if message.get('Cc') else []
                    all_recipients = to_recipients + cc_recipients
                    result = server.sendmail(username, all_recipients if all_recipients else message['To'], text)
                return result
    async def async_send_message(self, message, hostname: str, port: int, username: str, password: str, start_tls: bool = True, timeout: int = 30, recipients: list = None):
        raise NotImplementedError("SMTPLibClient does not support asynchronous sending. Use AioSMTPLibClient instead.")

class SendResult:
    def __init__(self, success: bool, message_id: str = None, error_detail: str = None, accepted_recipients: list = None, timestamp: float = None, exception: Exception = None):
        self.success = success
        self.message_id = message_id
        self.error_detail = error_detail
        self.accepted_recipients = accepted_recipients or []
        self.timestamp = timestamp or time.time()
        self.exception = exception
    def __repr__(self):
        return f"SendResult(success={self.success}, message_id={self.message_id}, error_detail={self.error_detail}, timestamp={self.timestamp})"
    def __bool__(self):
        return self.success
    def is_success(self) -> bool:
        return self.success
    def get_error(self) -> str:
        return self.error_detail

def _get_config_value(keys: List[str], sources: List[Dict[str, Any]]) -> Any:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is not None:
                return value
    return None

def _resolve_config(smtp_server: str = None, smtp_port: int = None, email: str = None, password: str = None, config_file: str = "email_config.json", config_dict: Dict[str, Any] = None, password_callback = None):
    env_vars = {
        'smtp_server': os.getenv('SMTP_SERVER'),
        'smtp_port': os.getenv('SMTP_PORT'),
        'email': os.getenv('SMTP_EMAIL'),
        'password': os.getenv('SMTP_PASSWORD')
    }
    file_config = {}
    if config_file:
        try:
            with open(config_file, 'r', encoding='utf-8-sig') as f:
                file_config = json.load(f)
        except FileNotFoundError:
            pass
        except json.JSONDecodeError as e:
            logger.warning(f"Config file {config_file} is malformed (JSON error): {e}")
        except Exception as e:
            logger.warning(f"Failed to load config file {config_file}: {e}")
    sources = [
        {'smtp_server': smtp_server, 'smtp_port': smtp_port, 'email': email, 'password': password},
        config_dict or {},
        env_vars,
        file_config
    ]
    final_smtp_server = _get_config_value(['smtp_server'], sources)
    final_smtp_port = _get_config_value(['smtp_port'], sources)
    final_email = _get_config_value(['email'], sources)
    final_password = _get_config_value(['password'], sources)
    if final_smtp_port is not None:
        try:
            final_smtp_port = int(str(final_smtp_port).strip())
        except (ValueError, TypeError):
            raise ConfigError(f"SMTP port must be an integer number, got: {final_smtp_port}")
    if final_password is None and password_callback is not None:
        final_password = password_callback()
    missing = []
    if not final_smtp_server:
        missing.append('smtp_server')
    if not final_smtp_port:
        missing.append('smtp_port')
    if not final_email:
        missing.append('email')
    if not final_password:
        missing.append('password')
    if missing:
        raise ConfigError(f"Missing required email configuration parameters: {', '.join(missing)}")
    return final_smtp_server, final_smtp_port, final_email, final_password

def _build_mime_message(from_email: str, to_emails: Union[str, List[str]], subject: str,
                        from_display_name: str = None, cc: List[str] = None,
                        bcc: List[str] = None, reply_to: str = None,
                        priority: Literal["high", "normal", "low"] = "normal") -> MIMEMultipart:
    msg = MIMEMultipart()
    msg['From'] = formataddr((from_display_name, from_email)) if from_display_name else from_email
    if isinstance(to_emails, list):
        to_str = ', '.join([formataddr((None, e)) for e in to_emails])
        msg['To'] = to_str
    else:
        msg['To'] = formataddr((None, to_emails))
    msg['Subject'] = subject
    if cc:
        cc_str = ', '.join([formataddr((None, e)) for e in cc])
        msg['Cc'] = cc_str
    if reply_to:
        msg.add_header('reply-to', reply_to)
    if priority == 'high':
        msg['X-Priority'] = '1'
        msg['Importance'] = 'High'
    elif priority == 'low':
        msg['X-Priority'] = '5'
        msg['Importance'] = 'Low'
    else:
        msg['X-Priority'] = '3'
        msg['Importance'] = 'Normal'
    return msg

def _add_content_to_message(msg: MIMEMultipart, content: Union[str, dict], content_type: str = "html") -> None:
    if isinstance(content, dict):
        if 'html' in content:
            msg.attach(MIMEText(content['html'], 'html'))
        if 'text' in content:
            msg.attach(MIMEText(content['text'], 'plain'))
    else:
        msg.attach(MIMEText(content, content_type))

def _process_attachment(file_path: str, max_size: int, ignore_errors: bool) -> Optional[MIMEBase]:
    try:
        size = os.path.getsize(file_path)
        if size > max_size:
            raise SizeLimitError(f"Attachment {file_path} exceeds size limit ({size} > {max_size} bytes)")
        with open(file_path, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        filename = os.path.basename(file_path)
        safe_filename = filename.replace('"', '\\"')
        part.add_header('Content-Disposition', f'attachment; filename="{safe_filename}"')
        return part
    except (FileNotFoundError, SizeLimitError, Exception) as e:
        if ignore_errors:
            logger.warning(f"Ignoring attachment error for {file_path}: {str(e)}")
            return None
        raise AttachmentError(f"Error processing attachment {file_path}: {str(e)}") from e

def _add_attachments_to_message(msg: MIMEMultipart, attachments: List[str], max_size: int, ignore_errors: bool) -> List[str]:
    errors = []
    if not attachments:
        return errors
    for path in attachments:
        part = _process_attachment(path, max_size, ignore_errors)
        if part is None:
            errors.append(f"Attachment {path} was skipped due to error")
        else:
            msg.attach(part)
    return errors

def _collect_recipients(to_emails: Union[str, List[str]], cc: List[str] = None, bcc: List[str] = None) -> List[str]:
    all_recipients = []
    if isinstance(to_emails, str):
        parsed = parseaddr(to_emails)[1]
        if parsed:
            all_recipients.append(parsed)
    else:
        for e in to_emails:
            parsed = parseaddr(e)[1]
            if parsed:
                all_recipients.append(parsed)
    if cc:
        for e in cc:
            parsed = parseaddr(e)[1]
            if parsed:
                all_recipients.append(parsed)
    if bcc:
        for e in bcc:
            parsed = parseaddr(e)[1]
            if parsed:
                all_recipients.append(parsed)
    return all_recipients

def validate_email_address(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def format_email_with_name(email: str, display_name: str = None) -> str:
    if display_name:
        return formataddr((display_name, email))
    return email

def validate_email_list(emails: Union[str, List[str]]) -> List[str]:
    if isinstance(emails, str):
        emails = [emails]
    invalid = []
    for email in emails:
        actual = parseaddr(email)[1] if email else ""
        if not actual or not validate_email_address(actual):
            invalid.append(email)
    if invalid:
        raise ValueError(f"Invalid email addresses: {', '.join(invalid)}")
    return emails

def get_password_securely(prompt: str = "请输入邮箱密码或授权码: ") -> str:
    try:
        import getpass
        return getpass.getpass(prompt)
    except ImportError:
        import sys
        if sys.stdin.isatty():
            print(prompt, end='', flush=True)
            import termios
            import tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                password = ""
                while True:
                    ch = sys.stdin.read(1)
                    if ch in '\r\n':
                        break
                    elif ch == '\x7f':
                        if password:
                            password = password[:-1]
                            print('\b \b', end='', flush=True)
                    elif ch == '\x03':
                        raise KeyboardInterrupt
                    else:
                        password += ch
                        print('*', end='', flush=True)
                print()
                return password
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        else:
            print(prompt, end='')
            return input()

class CreMail:
    def __init__(self, smtp_server: str = None, smtp_port: int = None, email: str = None, password: str = None, config_file: str = "email_config.json", config_dict: Dict[str, Any] = None, config_provider: ConfigProvider = None, max_attachment_size: int = 10 * 1024 * 1024, timeout: int = 30, use_tls: bool = True, use_ssl: bool = False, provider_priority: bool = False, from_display_name: str = None, smtp_client: SMTPClient = None, password_callback = None, log_file: str = None):
        if config_provider and provider_priority:
            config = config_provider.get_config()
            self.smtp_server, self.smtp_port, self.email, self.password = _resolve_config(
                smtp_server, smtp_port, email, password, config_file, config, password_callback
            )
        else:
            self.smtp_server, self.smtp_port, self.email, self.password = _resolve_config(
                smtp_server, smtp_port, email, password, config_file, config_dict, password_callback
            )
        self.max_attachment_size = max_attachment_size
        self.timeout = timeout
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.daily_send_limit = 1000
        self.rate_limit_delay = 1.0
        self.from_display_name = from_display_name
        self.smtp_client = smtp_client or SMTPLibClient()
        if log_file:
            abs_path = str(Path(log_file).absolute())
            if not any(
                isinstance(h, logging.FileHandler) and
                h.baseFilename == abs_path
                for h in logger.handlers
            ):
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
                logger.addHandler(file_handler)

    def validate_content(self, content: Union[str, dict]) -> None:
        if content is None:
            raise ContentValidationError("邮件内容不能为None")
        if isinstance(content, str):
            if not content or len(content.strip()) == 0:
                raise ContentValidationError("邮件内容不能为空")
        elif isinstance(content, dict):
            if not content.get('html', '').strip() and not content.get('text', '').strip():
                raise ContentValidationError("邮件内容不能为空")
        else:
            raise ContentValidationError("邮件内容必须是字符串或字典类型")

    async def batch_send(self, emails: List[Dict], batch_size: int = 10, max_concurrent: int = 5, stop_on_error: bool = False) -> List[SendResult]:
        semaphore = asyncio.Semaphore(max_concurrent)
        async def send_with_semaphore(email_data):
            async with semaphore:
                return await self._async_send_individual_email(**email_data)
        results = []
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i+batch_size]
            tasks = [asyncio.create_task(send_with_semaphore(data)) for data in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in batch_results:
                if isinstance(result, Exception):
                    send_result = SendResult(success=False, error_detail=str(result), exception=result)
                    results.append(send_result)
                    if stop_on_error:
                        logger.error(f"Stopping batch send due to error: {str(result)}")
                        return results
                else:
                    results.append(result)
                    if not result.success and stop_on_error and result.exception:
                        logger.error(f"Stopping batch send due to error: {str(result.error_detail)}")
                        return results
        return results

    async def _async_send_individual_email(
        self,
        recipient_email: str,
        subject: str,
        content: Union[str, dict],
        content_type: str = "html",
        attachments: List[str] = None,
        ignore_attachment_errors: bool = False,
        max_retries: int = 2,
        total_timeout: float = None,
        cc_recipients: List[str] = None,
        bcc_recipients: List[str] = None,
        reply_to: str = None,
        priority: Literal["high", "normal", "low"] = "normal"
    ) -> SendResult:
        self.validate_content(content)
        validate_email_list(recipient_email)
        if cc_recipients:
            validate_email_list(cc_recipients)
        if bcc_recipients:
            validate_email_list(bcc_recipients)
        all_recipients = _collect_recipients(recipient_email, cc_recipients, bcc_recipients)
        start_time = time.time()
        for attempt in range(max_retries + 1):
            try:
                msg = _build_mime_message(
                    self.email, recipient_email, subject,
                    self.from_display_name, cc_recipients, bcc_recipients, reply_to, priority
                )
                _add_content_to_message(msg, content, content_type)
                attach_errors = _add_attachments_to_message(msg, attachments or [], self.max_attachment_size, ignore_attachment_errors)
                if attach_errors and not ignore_attachment_errors:
                    raise AttachmentError(f"Attachment errors: {', '.join(attach_errors)}")
                if attach_errors and ignore_attachment_errors:
                    logger.warning(f"Ignoring attachment errors: {', '.join(attach_errors)}")
                await self.smtp_client.async_send_message(
                    msg,
                    hostname=self.smtp_server,
                    port=self.smtp_port,
                    username=self.email,
                    password=self.password,
                    start_tls=self.use_tls and not self.use_ssl,
                    timeout=self.timeout,
                    recipients=all_recipients
                )
                logger.info(f"Email sent successfully to {recipient_email}")
                return SendResult(success=True, message_id=str(hash(str(msg))), accepted_recipients=all_recipients)
            except Exception as e:
                logger.exception(f"Error sending email on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries:
                    return SendResult(success=False, error_detail=str(e), exception=e)
                if total_timeout is not None and (time.time() - start_time) >= total_timeout:
                    logger.warning("Total timeout exceeded")
                    return SendResult(success=False, error_detail="Total timeout exceeded")
                wait_time = min(2 ** attempt, 60) + random.uniform(0, 0.1 * min(2 ** attempt, 60))
                await asyncio.sleep(wait_time)
        return SendResult(success=False, error_detail="Max retries exceeded")

    def send_email(
        self,
        recipient_email: Union[str, List[str]],
        subject: str,
        content: Union[str, EmailContent],
        content_type: Literal["html", "plain"] = "html",
        attachments: List[str] = None,
        ignore_attachment_errors: bool = False,
        max_retries: int = 2,
        cc_recipients: List[str] = None,
        bcc_recipients: List[str] = None,
        reply_to: str = None,
        priority: Literal["high", "normal", "low"] = "normal",
        total_timeout: float = None
    ) -> SendResult:
        self.validate_content(content)
        validate_email_list(recipient_email)
        if cc_recipients:
            validate_email_list(cc_recipients)
        if bcc_recipients:
            validate_email_list(bcc_recipients)
        all_recipients = _collect_recipients(recipient_email, cc_recipients, bcc_recipients)
        start_time = time.time()
        for attempt in range(max_retries + 1):
            try:
                msg = _build_mime_message(
                    self.email, recipient_email, subject,
                    self.from_display_name, cc_recipients, bcc_recipients, reply_to, priority
                )
                _add_content_to_message(msg, content, content_type)
                attach_errors = _add_attachments_to_message(msg, attachments or [], self.max_attachment_size, ignore_attachment_errors)
                if attach_errors and not ignore_attachment_errors:
                    raise AttachmentError(f"Attachment errors: {', '.join(attach_errors)}")
                if attach_errors and ignore_attachment_errors:
                    logger.warning(f"Ignoring attachment errors: {', '.join(attach_errors)}")
                result = self.smtp_client.connect_and_send(
                    msg,
                    hostname=self.smtp_server,
                    port=self.smtp_port,
                    username=self.email,
                    password=self.password,
                    use_tls=self.use_tls,
                    use_ssl=self.use_ssl,
                    timeout=self.timeout,
                    recipients=all_recipients
                )
                logger.info(f"Email sent successfully to {recipient_email}")
                return SendResult(success=True, message_id=str(hash(str(msg))), accepted_recipients=list(result.keys()) if result else all_recipients)
            except smtplib.SMTPAuthenticationError as e:
                logger.exception(f"SMTP authentication error: {str(e)}")
                return SendResult(success=False, error_detail=f"SMTP authentication error: {str(e)}", exception=e)
            except smtplib.SMTPRecipientsRefused as e:
                logger.exception(f"Recipients refused: {str(e)}")
                return SendResult(success=False, error_detail=f"Recipients refused: {str(e)}", exception=e)
            except Exception as e:
                logger.exception(f"Error sending email on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries:
                    return SendResult(success=False, error_detail=str(e), exception=e)
                if total_timeout is not None and (time.time() - start_time) >= total_timeout:
                    logger.warning("Total timeout exceeded")
                    return SendResult(success=False, error_detail="Total timeout exceeded")
                wait_time = min(2 ** attempt, 60) + random.uniform(0, 0.1 * min(2 ** attempt, 60))
                time.sleep(wait_time)
        return SendResult(success=False, error_detail="Max retries exceeded")

def send_email_with_config(
    recipient_email: Union[str, List[str]],
    subject: str,
    content: Union[str, EmailContent],
    config_file: str = "email_config.json",
    content_type: Literal["html", "plain"] = "html",
    attachments: List[str] = None,
    ignore_attachment_errors: bool = False,
    max_retries: int = 2,
    cc_recipients: List[str] = None,
    bcc_recipients: List[str] = None,
    reply_to: str = None,
    priority: Literal["high", "normal", "low"] = "normal",
    password_callback = None
) -> SendResult:
    try:
        email_sender = CreMail(config_file=config_file, password_callback=password_callback)
        return email_sender.send_email(
            recipient_email, subject, content, content_type,
            attachments, ignore_attachment_errors, max_retries,
            cc_recipients, bcc_recipients, reply_to, priority
        )
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return SendResult(success=False, error_detail=str(e))

def generate_verification_code(length: int = 6) -> str:
    return generate_verification_code_unified(length, mode=VERIFICATION_CODE_DIGITS)

def generate_alphanumeric_verification_code(length: int = 6) -> str:
    return generate_verification_code_unified(length, mode=VERIFICATION_CODE_MIX)

def generate_letters_verification_code(length: int = 6) -> str:
    return generate_verification_code_unified(length, mode=VERIFICATION_CODE_LETTERS)

def generate_verification_code_unified(length: int = 6, mode: Literal['digits', 'letters', 'mix'] = 'digits') -> str:
    if mode == VERIFICATION_CODE_DIGITS:
        characters = string.digits
    elif mode == VERIFICATION_CODE_LETTERS:
        characters = string.ascii_letters
    elif mode == VERIFICATION_CODE_MIX:
        characters = string.digits + string.ascii_letters
    else:
        raise ValueError(f"Invalid mode. Use '{VERIFICATION_CODE_DIGITS}', '{VERIFICATION_CODE_LETTERS}', or '{VERIFICATION_CODE_MIX}'.")
    return ''.join([secrets.choice(characters) for _ in range(length)])

def render_template(template_file: str, data: Dict[str, Any]) -> str:
    if not _HAS_JINJA2:
        raise ImportError("jinja2 is required for template rendering. Install with: pip install jinja2")
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
        template = jinja2.Template(template_content)
        return template.render(**data)
    except Exception as e:
        raise ConfigError(f"Error rendering template: {str(e)}")

async def async_send_email(
    recipient_email: str,
    subject: str,
    content: Union[str, dict],
    smtp_server: str = None,
    smtp_port: int = None,
    email: str = None,
    password: str = None,
    config_file: str = "email_config.json",
    config_dict: Dict[str, Any] = None,
    content_type: str = "html",
    attachments: List[str] = None,
    ignore_attachment_errors: bool = False,
    max_retries: int = 2,
    max_attachment_size: int = 10 * 1024 * 1024,
    total_timeout: float = None,
    cc_recipients: List[str] = None,
    bcc_recipients: List[str] = None,
    reply_to: str = None,
    priority: Literal["high", "normal", "low"] = "normal",
    from_display_name: str = None
) -> SendResult:
    if not _HAS_AIOSMTPLIB:
        raise ImportError("aiosmtplib is required for async email sending. Install with: pip install aiosmtplib")
    sender = CreMail(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        email=email,
        password=password,
        config_file=config_file,
        config_dict=config_dict,
        max_attachment_size=max_attachment_size,
        from_display_name=from_display_name,
        smtp_client=AioSMTPLibClient()
    )
    return await sender._async_send_individual_email(
        recipient_email=recipient_email,
        subject=subject,
        content=content,
        content_type=content_type,
        attachments=attachments,
        ignore_attachment_errors=ignore_attachment_errors,
        max_retries=max_retries,
        total_timeout=total_timeout,
        cc_recipients=cc_recipients,
        bcc_recipients=bcc_recipients,
        reply_to=reply_to,
        priority=priority
    )

def get_default_sender(**kwargs) -> CreMail:
    global _default_sender
    with _default_sender_lock:
        if _default_sender is None:
            _default_sender = CreMail(**kwargs)
    return _default_sender

def send_email_with_default_sender(
    recipient_email: Union[str, List[str]],
    subject: str,
    content: Union[str, EmailContent],
    content_type: Literal["html", "plain"] = "html",
    attachments: List[str] = None,
    ignore_attachment_errors: bool = False,
    max_retries: int = 2,
    total_timeout: float = None,
    cc_recipients: List[str] = None,
    bcc_recipients: List[str] = None,
    reply_to: str = None,
    priority: Literal["high", "normal", "low"] = "normal"
) -> SendResult:
    sender = get_default_sender()
    return sender.send_email(
        recipient_email, subject, content, content_type,
        attachments, ignore_attachment_errors, max_retries,
        cc_recipients, bcc_recipients, reply_to, priority,
        total_timeout
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    try:
        email_sender = CreMail()
        logger.info("CreMail module is ready to use")
    except Exception as e:
        logger.error(f"Failed to initialize CreMail: {str(e)}")