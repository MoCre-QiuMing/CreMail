# CreMail 邮件发送模块

<div align="center">

[![中文](CreMail_zh.md)](CreMail_zh.md) | [![English](README.md)](README.md)

[![Python](https://img.shields.io/badge/Python-3.6%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**一个功能强大且易于使用的Python邮件发送模块**

✨ 支持多种配置方式  
🔧 支持同步和异步发送  
🚀 高性能批量发送  
📧 支持HTML和纯文本邮件  
🔒 高安全性的密码管理  
🎯 智能重试和错误处理  

</div>

## 📋 目录

- [特性](#-特性)
- [与其他邮件模块对比](#-与其他邮件模块对比)
- [安装](#-安装)
- [配置](#-配置)
- [使用方法](#-使用方法)
- [API参考](#-api参考)
- [示例](#-示例)
- [许可证](#-许可证)

## ✨ 特性

- **模块化设计**: 采用ConfigProvider协议，支持JSON、数据库、远程等多种配置源
- **高性能并发**: 支持异步发送和批量发送，内置信号量控制并发数
- **智能重试**: 支持指数退避和总超时控制，避免无限重试
- **安全密码管理**: 支持密码回调函数，避免密码在代码中硬编码
- **灵活内容**: 支持发送任意HTML/纯文本邮件内容，支持多格式内容
- **多种接口**: 基于类和基于函数的API，满足不同使用场景
- **可配置**: 支持配置文件、环境变量、字典参数等多种配置方式
- **验证码生成**: 提供数字、数字字母混合、纯英文字母三种验证码生成方式
- **附件支持**: 支持发送带附件的邮件，自动检查大小限制
- **异常体系**: 定义了详细的异常类，便于精准错误处理
- **SMTP抽象**: 支持SMTPClient协议，便于测试和扩展
- **显示名称**: 支持发件人和收件人显示名称
- **邮箱验证**: 发送前验证邮箱格式，避免无效地址
- **优先级支持**: 支持邮件优先级设置
- **全局实例**: 提供默认实例，减少重复配置

## 📊 与其他邮件模块对比

| 特性 | CreMail | smtplib | yagmail | aiosmtplib |
|------|---------|---------|---------|------------|
| 配置管理 | ✅ 高级 | ❌ 基础 | ✅ 中等 | ❌ 无 |
| 异步支持 | ✅ 完整 | ❌ 同步 | ❌ 同步 | ✅ 完整 |
| 批量发送 | ✅ 高性能 | ❌ 无 | ❌ 无 | ❌ 无 |
| 智能重试 | ✅ 高级 | ❌ 无 | ❌ 基础 | ❌ 无 |
| 并发控制 | ✅ 高级 | ❌ 无 | ❌ 无 | ❌ 无 |
| 密码安全 | ✅ 高级 | ❌ 基础 | ❌ 基础 | ❌ 基础 |
| 验证码生成 | ✅ 内置 | ❌ 无 | ❌ 无 | ❌ 无 |
| 模块化设计 | ✅ 高级 | ❌ 低 | ❌ 中等 | ❌ 低 |
| 显示名称 | ✅ 支持 | ✅ 支持 | ✅ 支持 | ❌ 无 |
| 邮箱验证 | ✅ 预发送验证 | ❌ 发送阶段验证 | ❌ 发送阶段验证 | ❌ 发送阶段验证 |

CreMail在功能完整性、安全性和易用性方面优于其他模块，适合需要高性能和高安全性的场景。

## 🚀 安装

1. 直接从GitHub安装：
   ```bash
   pip install git+https://github.com/MoCre-QiuMing/CreMail.git
   ```
   
2. 或者克隆或下载此仓库并将 `cremail.py` 复制到您的项目目录

## ⚙️ 配置

在项目根目录创建 `email_config.json` 文件，格式如下:

```json
{
  "smtp_server": "smtp.example.com",
  "smtp_port": 587,
  "email": "your_email@example.com",
  "password": "your_password_or_token"
}
```

### 常见邮箱提供商的SMTP服务器设置:

| 提供商 | SMTP服务器 | 端口 | SSL |
|--------|------------|------|-----|
| QQ邮箱 | smtp.qq.com | 587 | 是 |
| Gmail | smtp.gmail.com | 587 | 是 |
| 163邮箱 | smtp.163.com | 587 | 是 |
| Outlook | smtp-mail.outlook.com | 587 | 是 |

> **注意**: 对于QQ邮箱，"password" 字段应包含"授权码"而不是您的邮箱密码。您可以在QQ邮箱设置中获取。

## 📖 使用方法

### 方法1: 使用CreMail类

```python
from cremail import CreMail

# 使用配置文件初始化（默认: email_config.json）
sender = CreMail()

# 或使用直接参数初始化
sender = CreMail(
    smtp_server="smtp.qq.com",
    smtp_port=587,
    email="your_email@qq.com",
    password="your_authorization_code"
)

# 发送自定义邮件
success = sender.send_email(
    "user@example.com",
    "自定义主题",
    "<h1>你好!</h1><p>这是一封自定义HTML邮件。</p>",
    "html"
)

# 发送验证码邮件（使用验证码生成函数）
from cremail import generate_verification_code
verification_code = generate_verification_code()
verification_content = f"您的验证码是: <strong>{verification_code}</strong>，请在5分钟内使用。"
success = sender.send_email(
    "user@example.com",
    "验证码",
    verification_content,
    "html"
)
```

### 方法2: 使用常规函数

```python
from cremail import send_email_with_config

# 发送自定义邮件
success = send_email_with_config(
    "user@example.com",
    "标题",
    "<h1>自定义内容</h1>",
    "email_config.json",
    "html"
)
```

### 方法3: 使用验证码生成函数

```python
from cremail import CreMail, generate_verification_code, generate_alphanumeric_verification_code, generate_letters_verification_code, generate_verification_code_unified

sender = CreMail()

# 生成6位数字验证码
numeric_code = generate_verification_code(6)

# 生成8位数字字母混合验证码
alphanumeric_code = generate_alphanumeric_verification_code(8)

# 生成4位纯英文字母验证码
letters_code = generate_letters_verification_code(4)

# 使用统一API生成不同类型的验证码
unified_digits_code = generate_verification_code_unified(6, mode='digits')
unified_letters_code = generate_verification_code_unified(8, mode='letters')
unified_mix_code = generate_verification_code_unified(6, mode='mix')

# 创建包含不同类型验证码的邮件内容
numeric_content = f"您的数字验证码是: <strong>{numeric_code}</strong>，请在5分钟内使用。"
alphanumeric_content = f"您的数字字母验证码是: <strong>{alphanumeric_code}</strong>，请在5分钟内使用。"
letters_content = f"您的字母验证码是: <strong>{letters_code}</strong>，请在5分钟内使用。"

# 发送不同类型的验证码邮件
success1 = sender.send_email(
    "user1@example.com",
    "数字验证码",
    numeric_content,
    "html"
)

success2 = sender.send_email(
    "user2@example.com",
    "数字字母验证码",
    alphanumeric_content,
    "html"
)

success3 = sender.send_email(
    "user3@example.com",
    "字母验证码",
    letters_content,
    "html"
)
```

### 方法4: 发送带附件的邮件

```python
from cremail import CreMail

sender = CreMail()

# 发送带附件的邮件
success = sender.send_email(
    "user@example.com",
    "带附件的邮件",
    "请查收附件中的文件。",
    "plain",
    attachments=["path/to/file1.pdf", "path/to/file2.jpg"]  # 附件文件路径列表
)

# 发送带附件的邮件，但忽略附件错误（即使某些附件不存在也继续发送）
success = sender.send_email(
    "user@example.com",
    "带附件的邮件",
    "请查收附件中的文件。",
    "plain",
    attachments=["path/to/file1.pdf", "path/to/file2.jpg", "path/to/missing_file.pdf"],
    ignore_attachment_errors=True  # 忽略附件错误并继续发送邮件
)

# 也可以使用函数方式发送带附件的邮件
from cremail import send_email_with_config

success = send_email_with_config(
    "user@example.com",
    "带附件的邮件",
    "请查收附件中的文件。",
    "email_config.json",
    "plain",
    attachments=["path/to/file1.pdf", "path/to/file2.jpg"]
)

# 使用函数方式发送邮件并忽略附件错误
success = send_email_with_config(
    "user@example.com",
    "带附件的邮件",
    "请查收附件中的文件。",
    "email_config.json",
    "plain",
    attachments=["path/to/file1.pdf", "path/to/missing_file.pdf"],
    ignore_attachment_errors=True
)
```

### 方法5: 配置日志

```python
import logging
from cremail import CreMail

# 配置日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('cremail')
logger.setLevel(logging.INFO)

# 也可以添加自定义处理器
handler = logging.FileHandler('cremail.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

sender = CreMail()
result = sender.send_email(
    "user@example.com",
    "测试邮件",
    "这是一封测试邮件。",
    "plain"
)
print(f"发送结果: {result.success}, 详情: {result.error_detail}")
```

### 方法6: 使用环境变量配置

```python
import os
from cremail import CreMail

# 设置环境变量
os.environ['SMTP_SERVER'] = 'smtp.example.com'
os.environ['SMTP_PORT'] = '587'
os.environ['SMTP_EMAIL'] = 'your_email@example.com'
os.environ['SMTP_PASSWORD'] = 'your_password_or_token'

# 使用环境变量初始化
sender = CreMail()
result = sender.send_email(
    "user@example.com",
    "环境变量配置邮件",
    "这是一封使用环境变量配置发送的邮件。",
    "html"
)
```

### 方法7: 使用配置字典

```python
from cremail import CreMail

# 使用配置字典
config = {
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "email": "your_email@example.com",
    "password": "your_password_or_token"
}

sender = CreMail(config_dict=config)
result = sender.send_email(
    "user@example.com",
    "配置字典邮件",
    "这是一封使用配置字典发送的邮件。",
    "html"
)
```

### 方法8: 异常处理

```python
from cremail import CreMail, ConfigError, EmailSendError

try:
    sender = CreMail()
    result = sender.send_email(
        "user@example.com",
        "异常处理测试",
        "这是一封测试异常处理的邮件。",
        "html"
    )
    
    if not result.success:
        print(f"发送失败: {result.error_detail}")
    else:
        print(f"发送成功，消息ID: {result.message_id}")
        
except ConfigError as e:
    print(f"配置错误: {e}")
except EmailSendError as e:
    print(f"邮件发送错误: {e}")
except Exception as e:
    print(f"其他错误: {e}")
```

### 方法9: 使用重试机制

```python
from cremail import CreMail

sender = CreMail()
# 设置最大重试次数为3
result = sender.send_email(
    "user@example.com",
    "带重试机制的邮件",
    "这是一封使用重试机制发送的邮件。",
    "html",
    max_retries=3
)
```

### 方法10: 使用异步发送

```python
import asyncio
from cremail import async_send_email

async def send_async_email():
    result = await async_send_email(
        "user@example.com",
        "异步邮件",
        "这是一封异步发送的邮件。",
        smtp_server="smtp.qq.com",
        smtp_port=587,
        email="your_email@qq.com",
        password="your_authorization_code"
    )
    print(f"异步发送结果: {result.success}")

# 运行异步函数
asyncio.run(send_async_email())
```

### 方法11: 使用批量发送

```python
import asyncio
from cremail import CreMail

async def batch_send_example():
    sender = CreMail()
    
    emails = [
        {
            "recipient_email": "user1@example.com",
            "subject": "批量邮件1",
            "content": "这是批量发送的第一封邮件",
            "content_type": "plain"
        },
        {
            "recipient_email": "user2@example.com",
            "subject": "批量邮件2",
            "content": "这是批量发送的第二封邮件",
            "content_type": "plain"
        }
    ]
    
    results = await sender.batch_send(emails, batch_size=5, max_concurrent=3)
    for i, result in enumerate(results):
        print(f"邮件 {i+1} 发送结果: {result.success}")

# 运行异步函数
asyncio.run(batch_send_example())
```

## 📚 API参考

### 类: CreMail

#### `__init__(self, smtp_server=None, smtp_port=None, email=None, password=None, config_file="email_config.json", config_dict=None, config_provider=None, max_attachment_size=10485760, timeout=30, use_tls=True, use_ssl=False, provider_priority=False, from_display_name=None, smtp_client=None, password_callback=None)`

初始化邮件发送器。

**参数:**
- `smtp_server` (str, 可选): SMTP服务器地址
- `smtp_port` (int, 可选): SMTP服务器端口
- `email` (str, 可选): 发送者邮箱地址
- `password` (str, 可选): 发送者邮箱密码或授权码
- `config_file` (str): 配置文件路径 (默认: "email_config.json")
- `config_dict` (dict, 可选): 配置字典
- `config_provider` (ConfigProvider, 可选): 配置提供者
- `max_attachment_size` (int): 最大附件大小 (默认: 10MB)
- `timeout` (int): 连接超时时间 (默认: 30秒)
- `use_tls` (bool): 是否使用TLS (默认: True)
- `use_ssl` (bool): 是否使用SSL (默认: False)
- `provider_priority` (bool): 是否优先使用config_provider (默认: False)
- `from_display_name` (str, 可选): 发件人显示名称
- `smtp_client` (SMTPClient, 可选): SMTP客户端实现
- `password_callback` (callable, 可选): 密码获取回调函数

#### `send_email(self, recipient_email: Union[str, List[str]], subject: str, content: Union[str, dict], content_type: str = "html", attachments: List[str] = None, ignore_attachment_errors: bool = False, max_retries: int = 2, cc_recipients: List[str] = None, bcc_recipients: List[str] = None, reply_to: str = None, priority: Literal["high", "normal", "low"] = "normal", total_timeout: float = None) -> SendResult`

发送指定内容的自定义邮件。

**参数:**
- `recipient_email` (Union[str, List[str]]): 收件人邮箱地址或地址列表
- `subject` (str): 邮件主题
- `content` (Union[str, dict]): 邮件内容 (字符串或包含'html'和'text'键的字典)
- `content_type` (str): 内容类型 - "html" 或 "plain" (默认: "html")
- `attachments` (List[str], 可选): 附件文件路径列表
- `ignore_attachment_errors` (bool, 可选): 是否忽略附件错误并继续发送邮件 (默认: False)
- `max_retries` (int, 可选): 最大重试次数 (默认: 2)
- `cc_recipients` (List[str], 可选): 抄送列表
- `bcc_recipients` (List[str], 可选): 密送列表
- `reply_to` (str, 可选): 回复地址
- `priority` (Literal["high", "normal", "low"]): 邮件优先级 (默认: "normal")
- `total_timeout` (float, 可选): 总超时时间

**返回:**
- `SendResult`: 包含发送结果的对象

### 常规函数

#### `send_email_with_config(recipient_email, subject, content, config_file="email_config.json", content_type="html", attachments: List[str] = None, ignore_attachment_errors: bool = False, max_retries: int = 2, cc_recipients: List[str] = None, bcc_recipients: List[str] = None, reply_to: str = None, priority: Literal["high", "normal", "low"] = "normal", password_callback=None) -> SendResult`

使用配置文件发送邮件的常规函数。

#### `async_send_email(recipient_email, subject, content, smtp_server=None, smtp_port=None, email=None, password=None, config_file="email_config.json", config_dict=None, content_type="html", attachments: List[str] = None, ignore_attachment_errors: bool = False, max_retries: int = 2, max_attachment_size: int = 10485760, total_timeout: float = None, cc_recipients: List[str] = None, bcc_recipients: List[str] = None, reply_to: str = None, priority: Literal["high", "normal", "low"] = "normal", from_display_name: str = None) -> SendResult`

异步发送邮件的函数（需要安装aiosmtplib库）。

配置优先级：直接参数 > config_dict > 环境变量 > 配置文件

#### `render_template(template_file, data) -> str`

使用Jinja2渲染邮件模板（需要安装jinja2库）。

#### `generate_verification_code(length: int = 6) -> str`

生成指定长度的数字验证码（使用secrets模块增强安全性），可在邮件内容中使用。

#### `generate_alphanumeric_verification_code(length: int = 6) -> str`

生成指定长度的数字字母混合验证码（使用secrets模块增强安全性），可在邮件内容中使用。

#### `generate_letters_verification_code(length: int = 6) -> str`

生成指定长度的纯英文字母验证码（使用secrets模块增强安全性），可在邮件内容中使用。

#### `generate_verification_code_unified(length: int = 6, mode: str = 'digits') -> str`

统一的验证码生成函数，通过mode参数选择验证码类型。

**参数:**
- `length` (int): 验证码长度
- `mode` (str): 验证码类型，'digits'表示数字，'letters'表示字母，'mix'表示数字字母混合

**返回:**
- `str`: 生成的验证码字符串

### 自定义异常类

该模块定义了详细的异常类体系：

- `EmailSendError`: 邮件发送错误基类
- `ConfigError`: 配置错误
- `SMTPConnectionError`: SMTP连接错误
- `AttachmentError`: 附件处理错误
- `SizeLimitError`: 附件大小限制错误
- `RateLimitError`: 发送频率限制错误
- `ContentValidationError`: 内容验证错误

### SendResult类

发送邮件后返回SendResult对象，包含以下属性：

- `success` (bool): 发送是否成功
- `message_id` (str): 邮件消息ID
- `error_detail` (str): 错误详情
- `accepted_recipients` (list): 已接受的收件人列表
- `timestamp` (float): 发送时间戳
- `exception` (Exception): 原始异常对象

### 配置方式

支持多种配置方式，优先级如下：
1. 直接参数
2. config_dict
3. 环境变量
4. 配置文件

环境变量名称：
- `SMTP_SERVER`: SMTP服务器地址
- `SMTP_PORT`: SMTP服务器端口
- `SMTP_EMAIL`: 发送者邮箱
- `SMTP_PASSWORD`: 发送者密码或授权码

### 重试机制

send_email方法支持max_retries参数，默认为2次重试，使用指数退避算法和随机抖动。

### 异步支持

提供async_send_email异步函数和batch_send批量发送功能，需要安装aiosmtplib库。

### 模板渲染

提供render_template函数，需要安装jinja2库。

### 日志记录

该模块使用标准logging模块进行日志记录。主要日志事件包括：

- `INFO`: 邮件发送成功
- `WARNING`: 配置文件不存在
- `ERROR`: 配置文件格式错误、发送邮件失败、附件处理错误等

本模块使用名为 cremail 的日志记录器，您可以通过 logging.getLogger('cremail') 对其进行单独配置。

## 💡 示例

### 示例1: 发送欢迎邮件

```python
from cremail import CreMail

sender = CreMail()
success = sender.send_email(
    "newuser@example.com",
    "欢迎使用我们的服务!",
    """
    <html>
    <body>
        <h2>欢迎!</h2>
        <p>感谢您加入我们的服务。</p>
        <p>我们很高兴有您加入!</p>
    </body>
    </html>
    """,
    "html"
)
```

### 示例2: 发送通知邮件

```python
from cremail import send_email_with_config

success = send_email_with_config(
    "user@example.com",
    "系统通知",
    "<p>您的订单已成功提交，我们会尽快处理。</p>",
    "email_config.json",
    "html"
)
```

### 示例3: 发送数字验证码邮件

```python
from cremail import CreMail, generate_verification_code

sender = CreMail()

# 生成数字验证码
verification_code = generate_verification_code()

# 创建包含验证码的邮件内容
verification_content = f"""
<html>
<body>
    <h2>您的验证码</h2>
    <p>您好！</p>
    <p>您的验证码是: <strong style="font-size: 32px; color: #00aaff;">{verification_code}</strong></p>
    <p>此验证码将在10分钟内有效，请尽快使用。</p>
</body>
</html>
"""

success = sender.send_email(
    "user@example.com",
    "账户验证",
    verification_content,
    "html"
)
```

### 示例4: 发送数字字母混合验证码邮件

```python
from cremail import CreMail, generate_alphanumeric_verification_code

sender = CreMail()

# 生成数字字母混合验证码
verification_code = generate_alphanumeric_verification_code(8)

# 创建包含验证码的邮件内容
verification_content = f"""
<html>
<body>
    <h2>您的验证码</h2>
    <p>您好！</p>
    <p>您的验证码是: <strong style="font-size: 32px; color: #00aaff;">{verification_code}</strong></p>
    <p>此验证码将在10分钟内有效，请尽快使用。</p>
</body>
</html>
"""

success = sender.send_email(
    "user@example.com",
    "账户验证",
    verification_content,
    "html"
)
```

### 示例5: 发送纯英文字母验证码邮件

```python
from cremail import CreMail, generate_letters_verification_code

sender = CreMail()

# 生成纯英文字母验证码
verification_code = generate_letters_verification_code(6)

# 创建包含验证码的邮件内容
verification_content = f"""
<html>
<body>
    <h2>您的验证码</h2>
    <p>您好！</p>
    <p>您的验证码是: <strong style="font-size: 32px; color: #00aaff;">{verification_code}</strong></p>
    <p>此验证码将在10分钟内有效，请尽快使用。</p>
</body>
</html>
"""

success = sender.send_email(
    "user@example.com",
    "账户验证",
    verification_content,
    "html"
)
```

### 示例6: 发送纯文本邮件

```python
from cremail import CreMail

sender = CreMail()
success = sender.send_email(
    "user@example.com",
    "纯文本邮件",
    "这是一封纯文本邮件消息。",
    "plain"
)
```

### 示例7: 使用HTML和纯文本内容

```python
from cremail import CreMail

sender = CreMail()
content = {
    "html": "<h1>HTML内容</h1><p>这是HTML内容</p>",
    "text": "这是纯文本内容"
}
success = sender.send_email(
    "user@example.com",
    "双格式邮件",
    content,
    "html"
)
```

### 示例8: 发送带附件的邮件

```python
from cremail import CreMail

sender = CreMail()

# 发送带附件的邮件
success = sender.send_email(
    "user@example.com",
    "带附件的邮件",
    "请查收附件中的文件。",
    "plain",
    attachments=["path/to/file1.pdf", "path/to/file2.jpg"]  # 附件文件路径列表
)
```

### 示例9: 发送带附件的邮件（忽略附件错误）

```python
from cremail import CreMail

sender = CreMail()

# 发送带附件的邮件，但忽略附件错误（即使某些附件不存在也继续发送）
success = sender.send_email(
    "user@example.com",
    "带附件的邮件",
    "请查收附件中的文件。",
    "plain",
    attachments=["path/to/file1.pdf", "path/to/missing_file.pdf"],  # 其中一个附件不存在
    ignore_attachment_errors=True  # 忽略附件错误并继续发送邮件
)
```

### 示例10: 使用统一验证码API

```python
from cremail import CreMail, generate_verification_code_unified

sender = CreMail()

# 生成6位数字验证码
digits_code = generate_verification_code_unified(6, mode='digits')

# 生成8位纯字母验证码
letters_code = generate_verification_code_unified(8, mode='letters')

# 生成6位数字字母混合验证码
mix_code = generate_verification_code_unified(6, mode='mix')

# 创建包含验证码的邮件内容
content = f"""
<html>
<body>
    <h2>您的验证码</h2>
    <p>数字验证码: <strong>{digits_code}</strong></p>
    <p>字母验证码: <strong>{letters_code}</strong></p>
    <p>混合验证码: <strong>{mix_code}</strong></p>
    <p>请在5分钟内使用。</p>
</body>
</html>
"""

success = sender.send_email(
    "user@example.com",
    "多种验证码",
    content,
    "html"
)
```

### 示例11: 使用异步发送

```python
import asyncio
from cremail import async_send_email

async def send_verification_email():
    result = await async_send_email(
        "user@example.com",
        "异步验证码邮件",
        "您的验证码是: 123456",
        config_file="email_config.json",
        content_type="plain"
    )
    print(f"异步发送结果: {result.success}, 错误: {result.error_detail}")

# 运行异步函数
asyncio.run(send_verification_email())
```

### 示例12: 使用批量发送

```python
import asyncio
from cremail import CreMail

async def batch_send_emails():
    sender = CreMail()
    
    emails = [
        {
            "recipient_email": "user1@example.com",
            "subject": "批量邮件1",
            "content": "这是批量发送的第一封邮件",
            "content_type": "plain"
        },
        {
            "recipient_email": "user2@example.com",
            "subject": "批量邮件2",
            "content": "这是批量发送的第二封邮件",
            "content_type": "plain"
        },
        {
            "recipient_email": "user3@example.com",
            "subject": "批量邮件3",
            "content": "这是批量发送的第三封邮件",
            "content_type": "plain"
        }
    ]
    
    # 批量发送，限制并发数为2
    results = await sender.batch_send(emails, batch_size=2, max_concurrent=2)
    
    for i, result in enumerate(results):
        print(f"邮件 {i+1} 发送结果: {result.success}")
        if not result.success:
            print(f"  错误详情: {result.error_detail}")

# 运行异步函数
asyncio.run(batch_send_emails())
```

## 📄 许可证

本项目基于MIT许可证 - 详见 [LICENSE](LICENSE) 文件了解详情。

## 🤝 贡献

欢迎贡献！请随时提交Pull Request。对于重大更改，请先issue讨论您想要改变的内容。

## 🐛 问题

如果您遇到任何问题或对改进有建议，请在GitHub仓库中issue。