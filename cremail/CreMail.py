import base64
import smtplib
import socket
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
import mimetypes
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

_SENSITIVE_MASK = "******"

def _redact_sensitive(text, sensitive_values):
    """将 text 中出现的敏感值（密码/授权码等）替换为掩码，防止泄露到日志/错误信息。"""
    if not text:
        return text
    text = str(text)
    for val in sensitive_values:
        if isinstance(val, str) and len(val) >= 4:
            text = text.replace(val, _SENSITIVE_MASK)
    return text

def get_password_from_keyring(email, service="CreMail"):
    """从系统凭据存储(keyring)读取密码/授权码；未安装 keyring 或未找到时返回 None。"""
    try:
        import keyring
    except ImportError:
        logger.debug("keyring is not installed; falling back to config/env")
        return None
    try:
        return keyring.get_password(service, email)
    except Exception as e:
        logger.warning(f"Failed to read password from keyring: {e}")
        return None

def set_password_in_keyring(email, password, service="CreMail"):
    """将密码/授权码安全存入系统凭据存储(keyring)。返回 True 表示成功。"""
    try:
        import keyring
    except ImportError:
        raise ImportError("keyring is required to store passwords securely. Install with: pip install keyring")
    try:
        keyring.set_password(service, email, password)
        return True
    except Exception as e:
        raise ConfigError(f"Failed to store password in keyring: {e}") from e

def delete_password_from_keyring(email, service="CreMail"):
    """从 keyring 删除指定邮箱的密码记录。"""
    try:
        import keyring
    except ImportError:
        return False
    try:
        keyring.delete_password(service, email)
        return True
    except Exception:
        return False

def is_delivery_status_notification(message_text):
    """识别一封邮件是否为退信/送达状态通知(NDR/DSN)。
    检测：MAILER-DAEMON/postmaster 发件、multipart/report、message/delivery-status、
    reporting-mta/final-recipient/action: failed、退信关键词等。"""
    if not message_text:
        return False
    lowered = str(message_text).lower()
    markers = (
        "mailer-daemon", "postmaster",
        "multipart/report",
        "message/delivery-status",
        "reporting-mta",
        "final-recipient",
        "action: failed",
        "status: 4.", "status: 5.",
        "undelivered mail", "delivery failure",
        "退回", "退信", "未送达",
    )
    return any(m in lowered for m in markers)


def build_xoauth2_response(username: str, access_token: str) -> str:
    """构造 XOAUTH2 SASL 认证的初始响应文本（未做 base64 编码）。

    格式为 ``user=<邮箱>\\x01auth=Bearer <令牌>\\x01\\x01``，这是
    OAuth2 (XOAUTH2) SMTP 认证的标准载荷。用于 Gmail / Outlook / 其他
    支持 XOAUTH2 的 SMTP 服务。（2.3.0）
    """
    return f"user={username}\x01auth=Bearer {access_token}\x01\x01"


def _encode_xoauth2(username: str, access_token: str) -> str:
    """将 XOAUTH2 初始响应文本 base64 编码为可发送内容。"""
    return base64.b64encode(
        build_xoauth2_response(username, access_token).encode("utf-8")
    ).decode("ascii")


def _smtp_auth_xoauth2(server, username: str, access_token: str) -> None:
    """同步 smtplib 的 XOAUTH2 认证。access_token 为 OAuth2 访问令牌。"""
    def _authobject(challenge):
        if challenge:
            # 服务器返回了挑战/错误（base64 JSON），无法重试，发送空响应终止
            return b""
        return _encode_xoauth2(username, access_token)
    server.auth("XOAUTH2", _authobject)


async def _aio_auth_xoauth2(smtp, username: str, access_token: str) -> None:
    """异步 aiosmtplib 的 XOAUTH2 认证。

    通过 ``execute_command`` 手动发送 ``AUTH XOAUTH2 <base64>``，因为
    aiosmtplib 5.x 未提供通用的自定义 mechanism 认证入口。
    """
    initial = _encode_xoauth2(username, access_token)
    resp = await smtp.execute_command(b"AUTH", b"XOAUTH2", initial.encode("ascii"))
    if resp.code == 235:
        return
    if resp.code == 334:
        # 服务器请求后续输入（通常携带错误详情），发送空响应终止
        try:
            await smtp.execute_command(b"")
        except Exception:
            pass
    message = getattr(resp, "message", None)
    raise smtplib.SMTPAuthenticationError(
        resp.code, message if message is not None else "XOAUTH2 authentication failed"
    )


def _is_retryable_error(exc):
    """判定异常是否属于"瞬时/可重试"（网络超时、连接临时失败等）。
    确定性错误（认证失败、收件人拒绝、内容/附件/配置/限流错误）与
    服务端断开（受理状态未知）不重试。"""
    if isinstance(exc, (
        smtplib.SMTPAuthenticationError,
        smtplib.SMTPRecipientsRefused,
        ContentValidationError,
        AttachmentError,
        SizeLimitError,
        RateLimitError,
        ConfigError,
        ValueError,
    )):
        return False
    if isinstance(exc, smtplib.SMTPDataError):
        # DATA 阶段错误按响应码细分：4xx 临时错误可重试，5xx 永久错误不重试
        code = getattr(exc, 'smtp_code', 0) or 0
        return 400 <= code < 500
    if isinstance(exc, smtplib.SMTPServerDisconnected):
        return False
    if isinstance(exc, (socket.timeout, TimeoutError, OSError,
                        smtplib.SMTPConnectError,
                        smtplib.SMTPHeloError,
                        smtplib.SMTPResponseException)):
        return True
    if isinstance(exc, smtplib.SMTPException):
        return True
    return False

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
    'format_email_with_name',
    'get_password_from_keyring',
    'set_password_in_keyring',
    'delete_password_from_keyring',
    'is_delivery_status_notification'
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
    def connect_and_send(self, message, hostname: str, port: int, username: str, password: str, use_tls: bool = True, use_ssl: bool = False, timeout: int = 30, recipients: list = None, oauth2_token: str = None):
        ...
    async def async_send_message(self, message, hostname: str, port: int, username: str, password: str, start_tls: bool = True, timeout: int = 30, recipients: list = None, keep_alive: bool = None, oauth2_token: str = None):
        ...

class AioSMTPLibClient:
    """异步 aiosmtplib 客户端。

    并发安全与认证：
    - 默认（keep_alive=False）：每次发送创建独立连接，天然并发安全，多任务可真正并行。
    - keep_alive=True：复用单一连接；新增 _authenticated 标记，复用连接跳过重复 AUTH，
      避免二次登录被服务端拒绝（503 Already authenticated）。复用连接本身不适合并发（单连接语义）。
    """

    def __init__(self, keep_alive: bool = False):
        self.keep_alive = keep_alive
        self._smtp = None
        self._authenticated = False
        # 标记：不支持同步发送，send_email 入口据此报清晰错误而非运行时 NotImplementedError
        self.supports_sync = False

    def _make_smtp(self, hostname, port, start_tls, use_ssl, timeout):
        return aiosmtplib.SMTP(
            hostname=hostname,
            port=port,
            use_tls=use_ssl,
            start_tls=start_tls and not use_ssl,
            timeout=timeout,
        )

    @staticmethod
    def _collect_recipients(message):
        to = [parseaddr(addr.strip())[1] for addr in message['To'].split(',')] if message.get('To') else []
        cc = [parseaddr(addr.strip())[1] for addr in message.get('Cc', '').split(',')] if message.get('Cc') else []
        return to + cc

    async def _auth(self, smtp, username, password, oauth2_token, reuse):
        if oauth2_token:
            await _aio_auth_xoauth2(smtp, username, oauth2_token)
        elif not (reuse and self._authenticated):
            await smtp.login(username, password)
        if reuse:
            self._authenticated = True

    async def _send_on_smtp(self, smtp, message, username, password, recipients, oauth2_token, reuse):
        if not recipients:
            recipients = self._collect_recipients(message)
        await self._auth(smtp, username, password, oauth2_token, reuse)
        await smtp.send_message(message, recipients=recipients)

    @staticmethod
    async def _aio_close(smtp):
        try:
            await smtp.quit()
        except Exception:
            try:
                smtp.close()
            except Exception:
                pass

    async def async_send_message(self, message, hostname: str, port: int, username: str, password: str, start_tls: bool = True, use_ssl: bool = False, timeout: int = 30, recipients: list = None, keep_alive: bool = None, oauth2_token: str = None):
        if not _HAS_AIOSMTPLIB:
            raise ImportError("aiosmtplib is required for async email sending. Install with: pip install aiosmtplib")
        use_keep = self.keep_alive if keep_alive is None else keep_alive
        if use_keep:
            if self._smtp is None:
                self._smtp = self._make_smtp(hostname, port, start_tls, use_ssl, timeout)
                await self._smtp.connect()
                self._authenticated = False
            try:
                await self._send_on_smtp(self._smtp, message, username, password, recipients, oauth2_token, reuse=True)
            except Exception:
                await self.aclose()
                raise
            return
        # 默认：每次独立连接，并发安全
        smtp = self._make_smtp(hostname, port, start_tls, use_ssl, timeout)
        await smtp.connect()
        try:
            await self._send_on_smtp(smtp, message, username, password, recipients, oauth2_token, reuse=False)
        finally:
            await self._aio_close(smtp)

    async def aclose(self):
        """显式关闭并释放持有的异步 SMTP 连接（keep_alive=True 时复用连接）。幂等。"""
        smtp = self._smtp
        self._smtp = None
        self._authenticated = False
        if smtp is not None:
            await self._aio_close(smtp)

    def connect_and_send(self, message, hostname: str, port: int, username: str, password: str, use_tls: bool = True, use_ssl: bool = False, timeout: int = 30, recipients: list = None):
        raise NotImplementedError("AioSMTPLibClient does not support synchronous sending. Use SMTPLibClient instead.")

class SMTPLibClient:
    """同步 smtplib 客户端。

    并发安全策略：
    - 默认（keep_alive=False，即 batch_send 默认路径）：每次发送创建独立连接，天然并发安全，
      多任务可真正并行而不发生 SMTP 协议错乱。
    - keep_alive=True：复用单一连接，发送全程以 self._lock 串行化（复用连接本身不适合并发）。
    """

    def __init__(self, keep_alive: bool = False):
        self.keep_alive = keep_alive
        self._server = None
        self._lock = threading.Lock()
        # 标记：支持同步发送
        self.supports_sync = True

    def _new_server(self, hostname, port, use_tls, use_ssl, timeout):
        if use_ssl:
            return smtplib.SMTP_SSL(hostname, port, timeout=timeout)
        server = smtplib.SMTP(hostname, port, timeout=timeout)
        if use_tls:
            server.starttls()
        return server

    def _get_server(self, hostname, port, use_tls, use_ssl, timeout):
        # keep_alive 复用路径：获取/重建缓存的共享连接（调用方持有 self._lock 时执行）
        server = self._server
        if server is not None:
            try:
                server.noop()
                return server
            except Exception:
                self._server = None
                try:
                    server.close()
                except Exception:
                    pass
        server = self._new_server(hostname, port, use_tls, use_ssl, timeout)
        self._server = server
        return server

    @staticmethod
    def _safe_close(server):
        try:
            server.quit()
        except Exception:
            try:
                server.close()
            except Exception:
                pass

    def _send_on_server(self, server, message, username, password, recipients, oauth2_token):
        if not getattr(server, '_cremail_authenticated', False):
            if oauth2_token:
                _smtp_auth_xoauth2(server, username, oauth2_token)
            else:
                server.login(username, password)
            server._cremail_authenticated = True
        text = message.as_string()
        if recipients:
            result = server.sendmail(username, recipients, text)
        else:
            to_recipients = [parseaddr(addr.strip())[1] for addr in message['To'].split(',')] if message.get('To') else []
            cc_recipients = [parseaddr(addr.strip())[1] for addr in message.get('Cc', '').split(',')] if message.get('Cc') else []
            all_recipients = to_recipients + cc_recipients
            result = server.sendmail(username, all_recipients if all_recipients else message['To'], text)
        return result

    def connect_and_send(self, message, hostname: str, port: int, username: str, password: str, use_tls: bool = True, use_ssl: bool = False, timeout: int = 30, recipients: list = None, keep_alive: bool = None, oauth2_token: str = None):
        use_keep = self.keep_alive if keep_alive is None else keep_alive
        if use_keep:
            # keep_alive：复用单一连接，发送全程加锁串行化，保证协议顺序
            with self._lock:
                server = self._get_server(hostname, port, use_tls, use_ssl, timeout)
                try:
                    return self._send_on_server(server, message, username, password, recipients, oauth2_token)
                except Exception:
                    self._drop_server(server)
                    raise
        # 默认：每次独立新连接，并发安全
        server = self._new_server(hostname, port, use_tls, use_ssl, timeout)
        try:
            return self._send_on_server(server, message, username, password, recipients, oauth2_token)
        finally:
            self._safe_close(server)

    def _drop_server(self, server):
        # 调用方已持有 self._lock（keep_alive 发送异常路径），这里不再自锁，避免非重入锁死锁
        if self._server is server:
            self._server = None
        self._safe_close(server)

    def _close_server(self):
        with self._lock:
            server = self._server
            self._server = None
            if server is not None:
                self._safe_close(server)

    def close(self):
        """显式关闭并释放持有的 SMTP 连接（keep_alive=True 时复用连接）。幂等，可安全重复调用。"""
        self._close_server()

    async def async_send_message(self, message, hostname: str, port: int, username: str, password: str, start_tls: bool = True, use_ssl: bool = False, timeout: int = 30, recipients: list = None, keep_alive: bool = None, oauth2_token: str = None):
        """SMTPLibClient 的异步实现：将同步 connect_and_send 放入线程池执行，
        使默认客户端（零依赖）的 batch_send / 异步发送开箱即用。"""
        return await asyncio.to_thread(
            self.connect_and_send,
            message, hostname, port, username, password,
            use_tls=start_tls, use_ssl=use_ssl, timeout=timeout,
            recipients=recipients, keep_alive=keep_alive, oauth2_token=oauth2_token
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

def _resolve_config(smtp_server: str = None, smtp_port: int = None, email: str = None, password: str = None, config_file: str = "email_config.json", config_dict: Dict[str, Any] = None, password_callback = None, password_from_keyring: bool = False, oauth2_token: str = None):
    env_vars = {
        'smtp_server': os.getenv('SMTP_SERVER'),
        'smtp_port': os.getenv('SMTP_PORT'),
        'email': os.getenv('SMTP_EMAIL'),
        'password': os.getenv('SMTP_PASSWORD'),
        'oauth2_token': os.getenv('SMTP_OAUTH2_TOKEN')
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
        {'smtp_server': smtp_server, 'smtp_port': smtp_port, 'email': email, 'password': password, 'oauth2_token': oauth2_token},
        config_dict or {},
        env_vars,
        file_config
    ]
    final_smtp_server = _get_config_value(['smtp_server'], sources)
    final_smtp_port = _get_config_value(['smtp_port'], sources)
    final_email = _get_config_value(['email'], sources)
    final_password = _get_config_value(['password'], sources)
    final_oauth2_token = _get_config_value(['oauth2_token'], sources)
    if final_smtp_port is not None:
        try:
            final_smtp_port = int(str(final_smtp_port).strip())
        except (ValueError, TypeError):
            raise ConfigError(f"SMTP port must be an integer number, got: {final_smtp_port}")
    if final_password is None and password_callback is not None:
        final_password = password_callback()
    if final_password is None and password_from_keyring and final_email:
        final_password = get_password_from_keyring(final_email)
    missing = []
    if not final_smtp_server:
        missing.append('smtp_server')
    if not final_smtp_port:
        missing.append('smtp_port')
    if not final_email:
        missing.append('email')
    # OAuth2 认证时无需密码：只要提供了 access_token 即可（2.3.0）
    if not final_password and not final_oauth2_token:
        missing.append('password (or oauth2_token)')
    if missing:
        raise ConfigError(f"Missing required email configuration parameters: {', '.join(missing)}")
    return final_smtp_server, final_smtp_port, final_email, final_password, final_oauth2_token

def _build_mime_message(from_email: str, to_emails: Union[str, List[str]], subject: str,
                        from_display_name: str = None, cc: List[str] = None,
                        bcc: List[str] = None, reply_to: str = None,
                        priority: Literal["high", "normal", "low"] = "normal") -> MIMEMultipart:
    msg = MIMEMultipart()
    # BCC 故意不写入邮件头（RFC 5322），仅通过 sendmail 的收件人列表传递，避免泄露密送地址
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
        name, addr = parseaddr(reply_to)
        msg['Reply-To'] = formataddr((name, addr)) if name else addr
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
        # 用 multipart/alternative 分层：plain 在前、html 在后，客户端自动选择最佳呈现，避免纯文本与 HTML 平铺重复显示
        alt = MIMEMultipart('alternative')
        if content.get('text'):
            alt.attach(MIMEText(content['text'], 'plain'))
        if content.get('html'):
            alt.attach(MIMEText(content['html'], 'html'))
        msg.attach(alt)
    else:
        msg.attach(MIMEText(content, content_type))

def _process_attachment(file_path: str, max_size: int, ignore_errors: bool) -> Optional[MIMEBase]:
    try:
        size = os.path.getsize(file_path)
        if size > max_size:
            raise SizeLimitError(f"Attachment {file_path} exceeds size limit ({size} > {max_size} bytes)")
        mime_type, _ = mimetypes.guess_type(file_path)
        maintype, subtype = (mime_type or 'application/octet-stream').split('/', 1)
        with open(file_path, "rb") as f:
            part = MIMEBase(maintype, subtype)
            part.set_payload(f.read())
        encoders.encode_base64(part)
        filename = os.path.basename(file_path)
        # 让 email 模块按 RFC 2231 编码 filename 参数，中文附件名在 Outlook 等客户端不乱码
        part.add_header('Content-Disposition', 'attachment', filename=filename)
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
    # 宽松预校验：允许 user@localhost / 内网单段域名（TLD 可选），最终以服务端 RCPT 结果为准
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})?$'
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
            raise RuntimeError(
                "Non-interactive terminal: cannot read password securely. "
                "Provide it via config file, environment variable (SMTP_*), or keyring instead."
            )

class CreMail:
    def __init__(self, smtp_server: str = None, smtp_port: int = None, email: str = None, password: str = None, config_file: str = "email_config.json", config_dict: Dict[str, Any] = None, config_provider: ConfigProvider = None, max_attachment_size: int = 10 * 1024 * 1024, timeout: int = 30, use_tls: bool = True, use_ssl: bool = False, provider_priority: bool = False, from_display_name: str = None, smtp_client: SMTPClient = None, password_callback = None, log_file: str = None, keep_alive: bool = False, password_from_keyring: bool = False, oauth2_token: str = None, retry_delay_base: float = 2.0, retry_delay_max: float = 60.0, retry_jitter: float = 1.0):
        if config_provider and not provider_priority:
            logger.warning("config_provider provided but provider_priority=False; it will be ignored. "
                           "Pass provider_priority=True to use it.")
        if config_provider and provider_priority:
            config = config_provider.get_config()
            self.smtp_server, self.smtp_port, self.email, self.password, self.oauth2_token = _resolve_config(
                smtp_server, smtp_port, email, password, config_file, config, password_callback,
                password_from_keyring=password_from_keyring, oauth2_token=oauth2_token,
            )
        else:
            self.smtp_server, self.smtp_port, self.email, self.password, self.oauth2_token = _resolve_config(
                smtp_server, smtp_port, email, password, config_file, config_dict, password_callback,
                password_from_keyring=password_from_keyring, oauth2_token=oauth2_token,
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
        # 限流并发竞态防护：_next_send_at 原子预占时间槽；锁保护上限检查与间隔判定，避免并发批量同时发出
        self._next_send_at = 0.0
        self._throttle_lock = threading.Lock()
        self._athrottle_lock = None   # asyncio.Lock 懒创建（需在事件循环内）
        self.from_display_name = from_display_name
        self.keep_alive = keep_alive
        self.retry_delay_base = retry_delay_base
        self.retry_delay_max = retry_delay_max
        self.retry_jitter = retry_jitter
        # 用于日志脱敏：密码/授权码、OAuth2令牌与邮箱地址不出现于日志、错误信息
        self._sensitive_values = [v for v in (self.email, self.password, self.oauth2_token) if v]
        self.smtp_client = smtp_client or SMTPLibClient(keep_alive=keep_alive)
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

    def close(self) -> None:
        """显式关闭同步 SMTP 连接（keep_alive=True 时释放复用连接）。幂等，可安全重复调用。"""
        if hasattr(self.smtp_client, 'close'):
            self.smtp_client.close()

    async def aclose(self) -> None:
        """显式关闭异步 SMTP 连接（keep_alive=True 时释放复用连接）。幂等。"""
        if hasattr(self.smtp_client, 'aclose'):
            await self.smtp_client.aclose()

    def __del__(self):
        # 兜底释放连接，避免 keep_alive 连接泄漏（忽略异常）
        try:
            self.close()
        except Exception:
            pass

    def _reserve_slot(self) -> float:
        """限流核心（须在调用方持锁时执行）：重置日期、检查上限、原子预占时间槽，返回需等待秒数。
        不在此递增 _sent_today：仅在发送成功后计数，失败/重试不消耗每日额度。"""
        today = time.strftime('%Y-%m-%d')
        if self._sent_date != today:
            self._sent_date = today
            self._sent_today = 0
        if self._sent_today >= self.daily_send_limit:
            raise RateLimitError(f"Daily send limit ({self.daily_send_limit}) reached")
        now = time.time()
        wait = max(0.0, self._next_send_at - now)
        self._next_send_at = max(now, self._next_send_at) + self.rate_limit_delay
        return wait

    def _throttle(self) -> None:
        """同步限流：单日发送上限 + 最小间隔。锁内原子预占时间槽，并发下不同调用依次拉开间隔，避免同时发出撞服务商频控。"""
        with self._throttle_lock:
            wait = self._reserve_slot()
        if wait > 0:
            time.sleep(wait)

    async def _athrottle(self) -> None:
        """异步限流：与 _throttle 语义一致，等待用 asyncio.sleep（非阻塞），供 batch_send / 异步发送路径使用。"""
        if self._athrottle_lock is None:
            self._athrottle_lock = asyncio.Lock()
        async with self._athrottle_lock:
            wait = self._reserve_slot()
        if wait > 0:
            await asyncio.sleep(wait)

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
        # 注意：batch 内的邮件通过 asyncio.gather 并行发出，stop_on_error 仅停止"后续 batch"，
        # 当前已创建并运行的 batch 任务仍会全部发送完成（避免已受理邮件漏发）。
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
        await self._athrottle()
        self.validate_content(content)
        validate_email_list(recipient_email)
        if cc_recipients:
            validate_email_list(cc_recipients)
        if bcc_recipients:
            validate_email_list(bcc_recipients)
        all_recipients = _collect_recipients(recipient_email, cc_recipients, bcc_recipients)
        msgid = make_msgid()
        # 消息构建与附件处理与网络无关，只做一次；确定性错误在此直接抛出，不进入重试
        msg = _build_mime_message(
            self.email, recipient_email, subject,
            self.from_display_name, cc_recipients, bcc_recipients, reply_to, priority
        )
        msg['Message-ID'] = msgid
        _add_content_to_message(msg, content, content_type)
        attach_errors = _add_attachments_to_message(msg, attachments or [], self.max_attachment_size, ignore_attachment_errors)
        # ignore_errors=False 时 _process_attachment 直接抛异常，attach_errors 非空仅发生于 ignore_errors=True，故此处只做告警
        if attach_errors:
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
                    recipients=all_recipients,
                    oauth2_token=self.oauth2_token
                )
                logger.info(f"Email sent successfully to {recipient_email}")
                self._sent_today += 1  # 仅成功计当日额度
                return SendResult(success=True, message_id=msgid, accepted_recipients=all_recipients)
            except Exception as e:
                safe = _redact_sensitive(str(e), self._sensitive_values)
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
                    logger.exception(f"SMTP connection closed during async send (delivery status unknown): {safe}")
                    return SendResult(
                        success=False,
                        error_detail=(
                            f"SMTP connection closed during send; the email MAY already be delivered. "
                            f"Message-ID={msgid}. Do NOT blindly retry the same message."
                        ),
                        exception=e,
                    )
                # 确定性错误不进入重试，直接返回
                if not _is_retryable_error(e):
                    logger.exception(f"Non-retryable error sending email: {safe}")
                    return SendResult(success=False, error_detail=safe, exception=e)
                logger.exception(f"Error sending email on attempt {attempt + 1}: {safe}")
                if attempt == max_retries:
                    return SendResult(success=False, error_detail=safe, exception=e)
                if total_timeout is not None and (time.time() - start_time) >= total_timeout:
                    logger.warning("Total timeout exceeded")
                    return SendResult(success=False, error_detail="Total timeout exceeded")
                wait_time = min(self.retry_delay_base * (2 ** attempt), self.retry_delay_max) \
                    + self.retry_jitter * random.uniform(0.5, 1.0)
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
        if not getattr(self.smtp_client, 'supports_sync', True):
            raise TypeError(
                "Current smtp_client does not support synchronous sending. "
                "Use async_send_email / await send_email instead, or pass an SMTPLibClient."
            )
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
        # ignore_errors=False 时 _process_attachment 直接抛异常，attach_errors 非空仅发生于 ignore_errors=True，故此处只做告警
        if attach_errors:
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
                    recipients=all_recipients,
                    oauth2_token=self.oauth2_token
                )
                logger.info(f"Email sent successfully to {recipient_email}")
                if result:
                    # smtplib.sendmail() 返回"被拒收者字典"；非空即存在部分拒收。
                    # accepted_recipients 应表示真正被接受的地址，而非拒收者。
                    refused = list(result.keys())
                    accepted = [r for r in all_recipients if r not in refused]
                    detail = "; ".join(f"{addr}: {err}" for addr, err in result.items())
                    logger.warning(f"Some recipients refused: {detail}")
                    return SendResult(
                        success=False, message_id=msgid, accepted_recipients=accepted,
                        error_detail=f"Some recipients refused: {detail}"
                    )
                self._sent_today += 1  # 仅成功计当日额度
                return SendResult(success=True, message_id=msgid, accepted_recipients=all_recipients)
            except smtplib.SMTPAuthenticationError as e:
                safe = _redact_sensitive(str(e), self._sensitive_values)
                logger.exception(f"SMTP authentication error: {safe}")
                return SendResult(success=False, error_detail=f"SMTP authentication error: {safe}", exception=e)
            except smtplib.SMTPRecipientsRefused as e:
                safe = _redact_sensitive(str(e), self._sensitive_values)
                logger.exception(f"Recipients refused: {safe}")
                return SendResult(success=False, error_detail=f"Recipients refused: {safe}", exception=e)
            except smtplib.SMTPServerDisconnected as e:
                # 关键可靠性：服务器可能在"已受理邮件后"才断开（如 QQ 短时频控）。
                # 连接期/传输期被断无法可靠判定是否已投递，保守处理：不再盲目重试，避免重复发送。
                safe = _redact_sensitive(str(e), self._sensitive_values)
                logger.exception(f"SMTP connection closed during send (delivery status unknown): {safe}")
                return SendResult(
                    success=False,
                    error_detail=(
                        f"SMTP connection closed during send; the email MAY already be delivered. "
                        f"Message-ID={msgid}. Do NOT blindly retry the same message."
                    ),
                    exception=e,
                )
            except Exception as e:
                safe = _redact_sensitive(str(e), self._sensitive_values)
                # 确定性错误（认证/收件人拒绝/内容/附件/配置等）不进入重试，直接返回
                if not _is_retryable_error(e):
                    logger.exception(f"Non-retryable error sending email: {safe}")
                    return SendResult(success=False, error_detail=safe, exception=e)
                logger.exception(f"Error sending email on attempt {attempt + 1}: {safe}")
                if attempt == max_retries:
                    return SendResult(success=False, error_detail=safe, exception=e)
                if total_timeout is not None and (time.time() - start_time) >= total_timeout:
                    logger.warning("Total timeout exceeded")
                    return SendResult(success=False, error_detail="Total timeout exceeded")
                wait_time = min(self.retry_delay_base * (2 ** attempt), self.retry_delay_max) \
                    + self.retry_jitter * random.uniform(0.5, 1.0)
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
    use_ssl: bool = False,
    retry_delay_base: float = 2.0,
    retry_delay_max: float = 60.0,
    retry_jitter: float = 1.0,
    keep_alive: bool = False,
    password_from_keyring: bool = False,
    oauth2_token: str = None
) -> SendResult:
    email_sender = CreMail(
        config_file=config_file,
        password_callback=password_callback,
        timeout=timeout,
        max_attachment_size=max_attachment_size,
        use_tls=use_tls,
        use_ssl=use_ssl,
        keep_alive=keep_alive,
        password_from_keyring=password_from_keyring,
        oauth2_token=oauth2_token,
        retry_delay_base=retry_delay_base,
        retry_delay_max=retry_delay_max,
        retry_jitter=retry_jitter,
    )
    try:
        return email_sender.send_email(
            recipient_email, subject, content, content_type,
            attachments, ignore_attachment_errors, max_retries,
            cc_recipients, bcc_recipients, reply_to, priority, total_timeout
        )
    finally:
        # keep_alive=True 时该函数式路径不复用连接，主动 close 防止 socket 泄漏（不依赖 __del__ 兜底）
        email_sender.close()

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
    timeout: int = 30,
    use_tls: bool = True,
    use_ssl: bool = False,
    keep_alive: bool = False,
    oauth2_token: str = None,
    password_callback=None,
    password_from_keyring: bool = False,
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
        timeout=timeout,
        use_tls=use_tls,
        use_ssl=use_ssl,
        keep_alive=keep_alive,
        oauth2_token=oauth2_token,
        password_callback=password_callback,
        password_from_keyring=password_from_keyring,
        smtp_client=AioSMTPLibClient(keep_alive=keep_alive)
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