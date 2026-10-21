# CreMail 更新日志

## 2.3.0 (2026-10-21)

本版相比 **2.2.1**，在保持既有能力的基础上，修复了以下 BUG 并提升了健壮性。

### 相比 2.2.1 修复的错误（P0）

- **并发批量发送不可靠**：默认 `SMTPLibClient` 与异步 `AioSMTPLibClient` 原先共享单一连接，`max_concurrent>1` 时多任务在同一个 socket 上交错发送 SMTP 命令导致协议错乱、随机失败。现改为默认（`keep_alive=False`）每次发送创建独立连接、天然并发安全；`keep_alive=True` 复用单一连接时全程加锁串行化。
- **异步 keep_alive 二次认证失败**：`AioSMTPLibClient` 复用连接时原先无条件 `login()`，第二封必现 `503 Already authenticated`。现新增 `_authenticated` 标记，复用连接跳过重复 AUTH。
- **keep_alive 异常死锁**：`SMTPLibClient` 在 `keep_alive=True` + 发送异常路径中，于已持锁线程内再次获取非重入锁，导致永久阻塞。`_drop_server` 不再自锁修复。
- **MIME 分层错误**：`content={'html':..., 'text':...}` 原将纯文本与 HTML 平铺 attach 到顶层 `multipart/mixed`，客户端会重复显示或把 HTML 当附件。现用 `multipart/alternative` 分层（plain 在前、html 在后）。
- **中文附件文件名乱码**：附件文件名含非 ASCII（中文）时原直接拼入 header value，Outlook 等客户端乱码。现交由 email 模块按 RFC 2231 编码 filename 参数。
- **并发限流失效**：`batch_send` 并发 + `rate_limit_delay>0` 时，多个 task 同时读取旧时间值、同时 sleep 后同时发出，限流形同虚设。现用锁原子预占时间槽（`_next_send_at`），真正拉开发送间隔。

### 相比 2.2.1 的健壮性改进（P1/P2）

- **附件 MIME 类型推断**：`_process_attachment` 改用 `mimetypes.guess_type()`，图片/PDF 等可预览，不再一律 `application/octet-stream`。
- **Reply-To 处理**：支持带显示名的回复地址（`Name <a@b.com>`），改用标准 `Reply-To` 头。
- **函数式 API 连接泄漏**：`send_email_with_config` 发送后主动 `close()`，不再依赖 `__del__` 兜底。
- **异步 API 参数对齐**：`async_send_email` 新增 `password_callback` / `password_from_keyring`，与同步路径一致。
- **config_provider 忽略提示**：传入 `config_provider` 但未设 `provider_priority=True` 时给出告警，避免"配置缺失"的误导。
- **异步客户端同步调用防护**：将 `AioSMTPLibClient` 传入后调用同步 `send_email`，入口直接抛清晰 `TypeError`，不再运行时 `NotImplementedError`。
- **重试分类细化**：`SMTPDataError` 按响应码细分——`4xx` 临时错误可重试、`5xx` 永久错误不重试。
- **非交互终端拒绝明文取密**：`get_password_securely` 在非 isatty 环境不再 `input()` 明文回显，改为报错并提示用配置文件/环境变量/keyring。
- **失败发送不计入每日限额**：`_sent_today` 仅在发送成功后递增，失败/重试不再消耗当日额度。
- **地址校验放宽**：`validate_email_address` 允许 `user@localhost` / 内网单段域名（TLD 可选），以服务端 RCPT 为准。
- **SMTPClient Protocol 签名对齐**：补全 `keep_alive` 参数，与实现一致。
- **单元测试环境兼容**：keyring 用例在无可用后端时跳过，不再硬失败。

### 验证

- 离线单元测试（mock SMTP，不产生真实外发）：**35/35 通过**。
- 并发 / 死锁 / 限流 / MIME / 中文附件名等修复点均通过针对性代码级验证。

## 2.2.1 (2026-10-20)

本版在 2.2.0 基础上新增 6 项能力：凭据安全治理、三级重试策略、连接复用（keep-alive）、异步/同步 API 对齐、送达语义与退信识别、OAuth2 认证支持。

### 新增能力

- **凭据安全治理**
  - 支持从系统凭据存储（keyring）读取/写入/删除密码或授权码：`get_password_from_keyring`、`set_password_in_keyring`、`delete_password_from_keyring`（可选依赖 `keyring`）。
  - `CreMail(..., password_from_keyring=True)` 可直接从 keyring 取密码，避免授权码明文落盘。
  - 新增敏感信息脱敏：密码/授权码与邮箱地址不再出现在日志与错误信息中。
  - 配置来源优先级：显式参数 → config_dict → 环境变量（SMTP_*）→ 配置文件 → keyring。

- **三级重试策略**
  - 确定性错误（认证失败、收件人拒绝、内容/附件/配置/限流错误）**直接返回、不重试**。
  - 服务端断开（受理状态未知）**不盲目重试**，返回"邮件可能已送达，请勿重发"。
  - 瞬时网络错误（超时、连接临时失败）**指数退避重试**，退避参数可配置：`retry_delay_base`、`retry_delay_max`、`retry_jitter`。

- **连接复用（keep-alive）**
  - `CreMail(..., keep_alive=True)` 复用 SMTP 连接，减少高频批量发送的握手开销；提供 `close()`（同步）/ `aclose()`（异步）显式释放，析构函数兜底释放。

- **异步/同步 API 对齐**
  - `async_send_email` 现透传 `timeout`、`use_tls`、`use_ssl`、`keep_alive`，与同步能力对齐。
  - `send_email_with_config` 新增透传 `retry_delay_*`、`keep_alive`、`password_from_keyring`。

- **送达语义与退信识别**
  - 明确文档化：`success=True` 仅代表服务端**受理**，不等于收件人已送达。
  - 新增 `is_delivery_status_notification()` 识别退信/送达状态通知（NDR/DSN），便于对退信做回执关联与处理。

- **OAuth2 认证支持**
  - 新增 XOAUTH2 SASL 认证：`CreMail(..., oauth2_token="...")` 直接使用 OAuth2 访问令牌（Access Token）发信，无需密码/授权码（适用于 Gmail / Outlook / 支持 XOAUTH2 的服务）。
  - 同步（smtplib）与异步（aiosmtplib）客户端均支持；令牌可经显式参数 / config_dict / 环境变量 `SMTP_OAUTH2_TOKEN` / 配置文件提供。
  - 新增 `build_xoauth2_response()` 构造 XOAUTH2 初始响应，并已在包顶层导出。
  - OAuth2 令牌自动纳入日志/错误脱敏范围。

### 修复与加固

- **异步发送必崩修复**：`AioSMTPLibClient.async_send_message` 将 `use_ssl=use_ssl` 传给 `aiosmtplib.SMTP(...)`，而 aiosmtplib 的参数名是 `use_tls`，导致异步发送必然 `TypeError`；已修正为 `use_tls=use_ssl`。
- **批量发送默认可用**：`SMTPLibClient.async_send_message` 原直接抛 `NotImplementedError`，导致默认客户端（零依赖）的 `batch_send` 每封失败；现改为 `asyncio.to_thread` 包装同步 `connect_and_send`，开箱即用。
- **部分拒收语义修正**：`send_email` 正确区分 `smtplib.sendmail()` 返回的"被拒收者字典"，`accepted_recipients` 现在表示真正被接受的地址，存在拒收时 `success=False` 并附拒收明细。
- **限流覆盖异步路径**：新增异步 `_athrottle()`（`asyncio.sleep` 非阻塞），`batch_send` / `_async_send_individual_email` 发送前执行单日上限与最小间隔限流。
- **`send_email_with_config` 不再吞错**：构造/校验类确定性错误（如 `ConfigError`）不再被吞成 `SendResult(success=False)`，与 `send_email` 语义一致（确定性错误抛异常、发送错误返回结果）。
- **Python 版本声明修正**：`requires-python` / `python_requires` 由 `>=3.6` 修正为 `>=3.8`（代码使用 `typing.TypedDict`/`Literal`，3.6/3.7 无法导入），classifiers 同步移除 3.6/3.7。
- **文档同步**：README / CreMail_zh 的 Python 徽章改为 3.8+、依赖安装说明改为 extras 按需安装（`[async]`/`[all]`）。

### 验证

- 离线单元测试（mock SMTP，不产生真实外发）：**35/35 通过**（含新增"异步 use_tls 参数回归""部分拒收语义回归"用例）。

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
