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
from email.utils import formataddr, parseaddr, make_msgid
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
    'get_password_securely',
    'validate_email_address',
    'validate_email_list',
    'format_email_with_name'
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
        raise NotImplementedError(
            "DatabaseConfigProvider is not implemented yet. "
            "Use JSONConfigProvider or pass config_dict / config_file instead."
        )

class RemoteConfigProvider:
    def __init__(self, api_endpoint: str):
        self.api_endpoint = api_endpoint
    def get_config(self) -> Dict[str, Any]:
        raise NotImplementedError(
            "RemoteConfigProvider is not implemented yet. "
            "Use JSONConfigProvider or pass config_dict / config_file instead."
        )

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
    async def async_send_message(self, message, hostname: str, port: int, username: str, password: str, start_tls: bool = True, use_ssl: bool = False, timeout: int = 30, recipients: list = None):
        if not _HAS_AIOSMTPLIB:
            raise ImportError("aiosmtplib is required for async email sending. Install with: pip install aiosmtplib")
        if not recipients:
            to_recipients = [parseaddr(addr.strip())[1] for addr in message['To'].split(',')] if message.get('To') else []
            cc_recipients = [parseaddr(addr.strip())[1] for addr in message.get('Cc', '').split(',')] if message.get('Cc') else []
            recipients = to_recipients + cc_recipients
        smtp = aiosmtplib.SMTP(
            hostname=hostname,
            port=port,
            use_tls=use_ssl,
            start_tls=start_tls and not use_ssl,
            timeout=timeout,
        )
        async with smtp:
            await smtp.login(username, password)
            await smtp.send_message(message, recipients=recipients)
    def connect_and_send(self, message, hostname: str, port: int, username: str, password: str, use_tls: bool = True, use_ssl: bool = False, timeout: int = 30, recipients: list = None):
        raise NotImplementedError("AioSMTPLibClient does not support synchronous sending. Use SMTPLibClient instead.")

class SMTPLibClient:
    def connect_and_send(self, message, hostname: str, port: int, username: str, password: str, use_tls: bool = True, use_ssl: bool = False, timeout: int = 30, recipients: list = None):
        if use_ssl:
            with smtplib.SMTP_SSL(hostname, port, timeout=timeout) as server:
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
    async def async_send_message(self, message, hostname: str, port: int, username: str, password: str, start_tls: bool = True, use_ssl: bool = False, timeout: int = 30, recipients: list = None):
        # 用线程池包装同步 connect_and_send，让默认客户端也能支持异步/批量发送（零依赖，不强制 aiosmtplib）
        return await asyncio.to_thread(
            self.connect_and_send, message, hostname, port, username, password,
            start_tls and not use_ssl, use_ssl, timeout, recipients,
        )

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
    except SizeLimitError:
        if ignore_errors:
            logger.warning(f"Ignoring attachment size-limit error for {file_path}")
            return None
        # 让超限异常独立传播，供调用方区分"超限"与其他附件错误
        raise
    except (FileNotFoundError, PermissionError, OSError) as e:
        if ignore_errors:
            logger.warning(f"Ignoring attachment error for {file_path}: {str(e)}")
            return None
        raise AttachmentError(f"Error processing attachment {file_path}: {str(e)}") from e
    except Exception as e:
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
    seen = set()
    def _add(email: str) -> None:
        parsed = parseaddr(email)[1] if email else ""
        if parsed and parsed not in seen:
            seen.add(parsed)
            all_recipients.append(parsed)
    if isinstance(to_emails, str):
        _add(to_emails)
    else:
        for e in to_emails:
            _add(e)
    if cc:
        for e in cc:
            _add(e)
    if bcc:
        for e in bcc:
            _add(e)
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
        self._sent_today = 0
        self._sent_date = None
        self._last_sent_time = None
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

    def _throttle(self) -> None:
        """简单限流：单日发送上限 + 同一实例两次发送之间的最小间隔（rate_limit_delay）。"""
        today = time.strftime('%Y-%m-%d')
        if self._sent_date != today:
            self._sent_date = today
            self._sent_today = 0
        if self._sent_today >= self.daily_send_limit:
            raise RateLimitError(f"Daily send limit ({self.daily_send_limit}) reached")
        now = time.time()
        if self._last_sent_time is not None and self.rate_limit_delay > 0:
            elapsed = now - self._last_sent_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
        self._last_sent_time = time.time()
        self._sent_today += 1

    async def _athrottle(self) -> None:
        """异步限流：与 _throttle 同语义，但用 asyncio.sleep 避免阻塞事件循环。"""
        today = time.strftime('%Y-%m-%d')
        if self._sent_date != today:
            self._sent_date = today
            self._sent_today = 0
        if self._sent_today >= self.daily_send_limit:
            raise RateLimitError(f"Daily send limit ({self.daily_send_limit}) reached")
        now = time.time()
        if self._last_sent_time is not None and self.rate_limit_delay > 0:
            elapsed = now - self._last_sent_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_sent_time = time.time()
        self._sent_today += 1

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
        await self._athrottle()
        msgid = make_msgid()
        # 消息构建与附件处理与网络无关，只做一次；确定性错误在此直接抛出，不进入重试
        msg = _build_mime_message(
            self.email, recipient_email, subject,
            self.from_display_name, cc_recipients, bcc_recipients, reply_to, priority
        )
        msg['Message-ID'] = msgid
        _add_content_to_message(msg, content, content_type)
        attach_errors = _add_attachments_to_message(msg, attachments or [], self.max_attachment_size, ignore_attachment_errors)
        if attach_errors and not ignore_attachment_errors:
            raise AttachmentError(f"Attachment errors: {', '.join(attach_errors)}")
        if attach_errors and ignore_attachment_errors:
            logger.warning(f"Ignoring attachment errors: {', '.join(attach_errors)}")
        start_time = time.time()
        for attempt in range(max_retries + 1):
            try:
                await self.smtp_client.async_send_message(
                    msg,
                    hostname=self.smtp_server,
                    port=self.smtp_port,
                    username=self.email,
                    password=self.password,
                    start_tls=self.use_tls and not self.use_ssl,
                    use_ssl=self.use_ssl,
                    timeout=self.timeout,
                    recipients=all_recipients
                )
                logger.info(f"Email sent successfully to {recipient_email}")
                return SendResult(success=True, message_id=msgid, accepted_recipients=all_recipients)
            except Exception as e:
                # 区分"连接被服务端关闭"：服务器可能已受理，返回状态未知，不盲目重试（避免重复投递）
                disconnect_types = []
                sync_dc = getattr(smtplib, 'SMTPServerDisconnected', None)
                if sync_dc is not None:
                    disconnect_types.append(sync_dc)
                if _HAS_AIOSMTPLIB:
                    try:
                        from aiosmtplib.errors import SMTPServerDisconnected as aio_dc
                        disconnect_types.append(aio_dc)
                    except Exception:
                        pass
                if any(isinstance(e, dt) for dt in disconnect_types):
                    logger.exception(f"SMTP connection closed during async send (delivery status unknown): {str(e)}")
                    return SendResult(
                        success=False,
                        error_detail=(
                            f"SMTP connection closed during send; the email MAY already be delivered. "
                            f"Message-ID={msgid}. Do NOT blindly retry the same message."
                        ),
                        exception=e,
                    )
                logger.exception(f"Error sending email on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries:
                    return SendResult(success=False, error_detail=str(e), exception=e)
                if total_timeout is not None and (time.time() - start_time) >= total_timeout:
                    logger.warning("Total timeout exceeded")
                    return SendResult(success=False, error_detail="Total timeout exceeded")
                wait_time = min(2 ** attempt, 60) + random.uniform(0.5, 2.0)
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
        # 约定：参数校验错误（非法收件人/空内容）与确定性资源错误（附件超限等）直接抛异常；
        #       发送/网络运行错误返回 SendResult(success=False)
        self.validate_content(content)
        validate_email_list(recipient_email)
        if cc_recipients:
            validate_email_list(cc_recipients)
        if bcc_recipients:
            validate_email_list(bcc_recipients)
        all_recipients = _collect_recipients(recipient_email, cc_recipients, bcc_recipients)
        self._throttle()
        # 幂等标识：同一封邮件（含重试）使用同一 Message-ID，便于服务端/用户去重与追踪
        msgid = make_msgid()
        # 消息构建与附件处理与网络无关，只做一次；确定性错误（超限/缺失）在此直接抛出，不进入重试
        msg = _build_mime_message(
            self.email, recipient_email, subject,
            self.from_display_name, cc_recipients, bcc_recipients, reply_to, priority
        )
        msg['Message-ID'] = msgid
        _add_content_to_message(msg, content, content_type)
        attach_errors = _add_attachments_to_message(msg, attachments or [], self.max_attachment_size, ignore_attachment_errors)
        if attach_errors and not ignore_attachment_errors:
            raise AttachmentError(f"Attachment errors: {', '.join(attach_errors)}")
        if attach_errors and ignore_attachment_errors:
            logger.warning(f"Ignoring attachment errors: {', '.join(attach_errors)}")
        start_time = time.time()
        for attempt in range(max_retries + 1):
            try:
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
                refused = result if result else {}  # smtplib.sendmail 返回 {被拒收地址: 原因}
                accepted = [r for r in all_recipients if r not in refused] if refused else all_recipients
                if refused:
                    logger.warning(f"部分收件人被拒收: {refused}")
                    return SendResult(success=False, message_id=msgid, error_detail=f"部分收件人被拒收: {refused}", accepted_recipients=accepted)
                logger.info(f"Email sent successfully to {recipient_email}")
                return SendResult(success=True, message_id=msgid, accepted_recipients=accepted)
            except smtplib.SMTPAuthenticationError as e:
                logger.exception(f"SMTP authentication error: {str(e)}")
                return SendResult(success=False, error_detail=f"SMTP authentication error: {str(e)}", exception=e)
            except smtplib.SMTPRecipientsRefused as e:
                logger.exception(f"Recipients refused: {str(e)}")
                return SendResult(success=False, error_detail=f"Recipients refused: {str(e)}", exception=e)
            except smtplib.SMTPServerDisconnected as e:
                # 关键可靠性：服务器可能在"已受理邮件后"才断开（如 QQ 短时频控）。
                # 连接期/传输期被断无法可靠判定是否已投递，保守处理：不再盲目重试，避免重复发送。
                logger.exception(f"SMTP connection closed during send (delivery status unknown): {str(e)}")
                return SendResult(
                    success=False,
                    error_detail=(
                        f"SMTP connection closed during send; the email MAY already be delivered. "
                        f"Message-ID={msgid}. Do NOT blindly retry the same message."
                    ),
                    exception=e,
                )
            except Exception as e:
                logger.exception(f"Error sending email on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries:
                    return SendResult(success=False, error_detail=str(e), exception=e)
                if total_timeout is not None and (time.time() - start_time) >= total_timeout:
                    logger.warning("Total timeout exceeded")
                    return SendResult(success=False, error_detail="Total timeout exceeded")
                wait_time = min(2 ** attempt, 60) + random.uniform(0.5, 2.0)
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
    password_callback = None,
    total_timeout: float = None,
    timeout: int = 30,
    max_attachment_size: int = 10 * 1024 * 1024,
    use_tls: bool = True,
    use_ssl: bool = False
) -> SendResult:
    email_sender = CreMail(
        config_file=config_file,
        password_callback=password_callback,
        timeout=timeout,
        max_attachment_size=max_attachment_size,
        use_tls=use_tls,
        use_ssl=use_ssl,
    )
    return email_sender.send_email(
        recipient_email, subject, content, content_type,
        attachments, ignore_attachment_errors, max_retries,
        cc_recipients, bcc_recipients, reply_to, priority, total_timeout
    )

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
    from_display_name: str = None,
    use_tls: bool = True,
    use_ssl: bool = False
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
        smtp_client=AioSMTPLibClient(),
        use_tls=use_tls,
        use_ssl=use_ssl,
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