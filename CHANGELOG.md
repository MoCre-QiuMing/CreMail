# CreMail 更新日志

## 2.2.0 (2026-10-20)

本版聚焦修复 2.1.2 代码审查发现的硬性 BUG 与潜在问题。

### 硬性 BUG 修复

- **收件人列表去重**：`_collect_recipients` 现在会按首次出现顺序去重，同一地址同时出现在
  to/cc/bcc 不再重复进 RCPT 列表，避免重复投递或被服务器拒绝。
- **发送结果判定可靠性（防重复发送）**：
  - 邮件现在携带真实的 `Message-ID`（由 `email.utils.make_msgid()` 生成），同一封邮件（含重试）
    复用同一 Message-ID，作为幂等标识；取代了原先无意义的 `hash(str(msg))`。
  - 当发送过程中服务端断开连接（`SMTPServerDisconnected` / 异步 `Unexpected EOF`）时，
    不再盲目指数退避重试——因为邮件可能已被服务端受理投递（如 QQ 短时频控下连接被断但已送达）。
    此时返回 `SendResult(success=False)` 且 `error_detail` 明确提示"邮件可能已送达，
    请勿盲目重发同一封"，避免重复投递。
  - 消息构建与附件处理移出重试循环（只做一次），确定性错误不进入无意义的重试。
- **附件异常分类**：`_process_attachment` 不再把 `SizeLimitError` 吞成通用 `AttachmentError`；
  超限错误会独立向外传播，调用方可区分"附件超限"与"文件缺失/IO 错误"。
  `except (FileNotFoundError, SizeLimitError, Exception)` 的冗余元组已修正。

### API 修复

- **工具函数导出**：`validate_email_address`、`validate_email_list`、`format_email_with_name`
  现在已加入包顶层 `__init__.py` 与 `__all__`，可直接 `from cremail import ...` 使用。
- **便捷函数补全参数**：`send_email_with_config` 新增并透传
  `total_timeout`、`timeout`、`max_attachment_size`、`use_tls`、`use_ssl`。
- **错误语义统一并文档化**：参数/确定性错误（非法收件人、空内容、附件超限）直接抛异常；
  发送/网络错误返回 `SendResult(success=False)`。

### 其他改进

- **版本号一致性**：`__init__.py`、`setup.py`、`pyproject.toml` 统一为 `2.2.0`。
- **限流真实生效**：`daily_send_limit` 与 `rate_limit_delay` 此前为死代码，现由 `_throttle()`
  真正执行（单日发送上限 + 同一实例两次发送最小间隔）。
- **异步客户端支持 SSL 端口**：`AioSMTPLibClient` 改用 `aiosmtplib.SMTP` 类，
  支持 `use_ssl=True`（465 端口），不再仅支持 STARTTLS。
- **移除死代码**：`SMTPLibClient` SSL 分支的空操作 `if use_tls: pass` 已删除。
- **占位 Provider 明确报错**：`DatabaseConfigProvider` / `RemoteConfigProvider`
  由"静默返回空配置"改为抛出 `NotImplementedError`，避免误用陷阱。
- **消除双份实现漂移**：顶层 `CreMail.py` 改为对 `cremail.CreMail` 的薄包装，
  不再与包内实现各存一份大文件。
- `setup.py` 的占位仓库地址修正为真实仓库。

### 验证

- 离线单元测试（mock SMTP，不产生真实外发）：36/36 通过。
- 真实冒烟测试（QQ SMTP → 目标邮箱）：发送成功，`message_id` 为真实 Message-ID 格式。
