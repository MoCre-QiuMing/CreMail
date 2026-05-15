CreMail 邮件发送模块
====================

.. image:: https://img.shields.io/badge/Python-3.6%2B-blue
   :target: https://www.python.org/
   :alt: Python

.. image:: https://img.shields.io/badge/License-MIT-green
   :target: LICENSE
   :alt: License

**一个功能强大且易于使用的 Python 邮件发送模块**

✨ 支持多种配置方式  
🔧 支持同步和异步发送  
🚀 高性能批量发送  
📧 支持 HTML 和纯文本邮件  
🔒 高安全性的密码管理  
🎯 智能重试和错误处理  

目录
----

.. contents:: 目录
   :depth: 2

特性
----

- **模块化设计**: 采用 ConfigProvider 协议，支持 JSON、数据库、远程等多种配置源
- **高性能并发**: 支持异步发送和批量发送，内置信号量控制并发数
- **智能重试**: 支持指数退避和总超时控制，避免无限重试
- **安全密码管理**: 支持密码回调函数，避免密码在代码中硬编码
- **灵活内容**: 支持发送任意 HTML/纯文本邮件内容，支持多格式内容
- **多种接口**: 基于类和基于函数的 API，满足不同使用场景
- **可配置**: 支持配置文件、环境变量、字典参数等多种配置方式
- **验证码生成**: 提供数字、数字字母混合、纯英文字母三种验证码生成方式
- **附件支持**: 支持发送带附件的邮件，自动检查大小限制
- **异常体系**: 定义了详细的异常类，便于精准错误处理
- **SMTP 抽象**: 支持 SMTPClient 协议，便于测试和扩展
- **显示名称**: 支持发件人和收件人显示名称
- **邮箱验证**: 发送前验证邮箱格式，避免无效地址
- **优先级支持**: 支持邮件优先级设置
- **全局实例**: 提供默认实例，减少重复配置

与其他邮件模块对比
------------------

.. list-table:: 特性对比
   :header-rows: 1
   :widths: 20 10 10 10 10

   * - 特性
     - CreMail
     - smtplib
     - yagmail
     - aiosmtplib
   * - 配置管理
     - ✅ 高级
     - ❌ 基础
     - ✅ 中等
     - ❌ 无
   * - 异步支持
     - ✅ 完整
     - ❌ 同步
     - ❌ 同步
     - ✅ 完整
   * - 批量发送
     - ✅ 高性能
     - ❌ 无
     - ❌ 无
     - ❌ 无
   * - 智能重试
     - ✅ 高级
     - ❌ 无
     - ❌ 基础
     - ❌ 无
   * - 并发控制
     - ✅ 高级
     - ❌ 无
     - ❌ 无
     - ❌ 无
   * - 密码安全
     - ✅ 高级
     - ❌ 基础
     - ❌ 基础
     - ❌ 基础
   * - 验证码生成
     - ✅ 内置
     - ❌ 无
     - ❌ 无
     - ❌ 无
   * - 模块化设计
     - ✅ 高级
     - ❌ 低
     - ❌ 中等
     - ❌ 低
   * - 显示名称
     - ✅ 支持
     - ✅ 支持
     - ✅ 支持
     - ❌ 无
   * - 邮箱验证
     - ✅ 预发送验证
     - ❌ 发送阶段验证
     - ❌ 发送阶段验证
     - ❌ 发送阶段验证

CreMail 在功能完整性、安全性和易用性方面优于其他模块，适合需要高性能和高安全性的场景。

安装
----

1. 直接从 GitHub 安装：

   .. code-block:: bash

      pip install git+https://github.com/MoCre-QiuMing/CreMail.git

2. 或者克隆或下载此仓库并将 ``cremail.py`` 复制到您的项目目录。

配置
----

在项目根目录创建 ``email_config.json`` 文件，格式如下：

.. code-block:: json

   {
     "smtp_server": "smtp.example.com",
     "smtp_port": 587,
     "email": "your_email@example.com",
     "password": "your_password_or_token"
   }

常见邮箱提供商的 SMTP 服务器设置
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: SMTP 服务器
   :header-rows: 1

   * - 提供商
     - SMTP 服务器
     - 端口
     - SSL
   * - QQ 邮箱
     - smtp.qq.com
     - 587
     - 是
   * - Gmail
     - smtp.gmail.com
     - 587
     - 是
   * - 163 邮箱
     - smtp.163.com
     - 587
     - 是
   * - Outlook
     - smtp-mail.outlook.com
     - 587
     - 是

.. note:: 对于 QQ 邮箱，"password" 字段应包含"授权码"而不是您的邮箱密码。您可以在 QQ 邮箱设置中获取。

使用方法
--------

方法1: 使用 CreMail 类
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

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

   # 发送验证码邮件
   from cremail import generate_verification_code
   verification_code = generate_verification_code()
   verification_content = f"您的验证码是: <strong>{verification_code}</strong>，请在5分钟内使用。"
   success = sender.send_email(
       "user@example.com",
       "验证码",
       verification_content,
       "html"
   )

方法2: 使用常规函数
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from cremail import send_email_with_config

   success = send_email_with_config(
       "user@example.com",
       "标题",
       "<h1>自定义内容</h1>",
       "email_config.json",
       "html"
   )

方法3: 使用验证码生成函数
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from cremail import CreMail, generate_verification_code, generate_alphanumeric_verification_code, generate_letters_verification_code, generate_verification_code_unified

   sender = CreMail()

   numeric_code = generate_verification_code(6)
   alphanumeric_code = generate_alphanumeric_verification_code(8)
   letters_code = generate_letters_verification_code(4)

   unified_digits_code = generate_verification_code_unified(6, mode='digits')
   unified_letters_code = generate_verification_code_unified(8, mode='letters')
   unified_mix_code = generate_verification_code_unified(6, mode='mix')

   # 发送不同类型的验证码邮件（省略具体内容）

方法4: 发送带附件的邮件
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from cremail import CreMail

   sender = CreMail()

   success = sender.send_email(
       "user@example.com",
       "带附件的邮件",
       "请查收附件中的文件。",
       "plain",
       attachments=["path/to/file1.pdf", "path/to/file2.jpg"]
   )

   # 忽略附件错误继续发送
   success = sender.send_email(
       "user@example.com",
       "带附件的邮件",
       "请查收附件中的文件。",
       "plain",
       attachments=["path/to/file1.pdf", "path/to/missing_file.pdf"],
       ignore_attachment_errors=True
   )

方法5: 配置日志
~~~~~~~~~~~~~~

.. code-block:: python

   import logging
   from cremail import CreMail

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger('cremail')
   logger.setLevel(logging.INFO)

   handler = logging.FileHandler('cremail.log')
   formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
   handler.setFormatter(formatter)
   logger.addHandler(handler)

   sender = CreMail()
   result = sender.send_email(...)

方法6: 使用环境变量配置
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import os
   from cremail import CreMail

   os.environ['SMTP_SERVER'] = 'smtp.example.com'
   os.environ['SMTP_PORT'] = '587'
   os.environ['SMTP_EMAIL'] = 'your_email@example.com'
   os.environ['SMTP_PASSWORD'] = 'your_password_or_token'

   sender = CreMail()
   result = sender.send_email(...)

方法7: 使用配置字典
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from cremail import CreMail

   config = {
       "smtp_server": "smtp.example.com",
       "smtp_port": 587,
       "email": "your_email@example.com",
       "password": "your_password_or_token"
   }

   sender = CreMail(config_dict=config)
   result = sender.send_email(...)

方法8: 异常处理
~~~~~~~~~~~~~~

.. code-block:: python

   from cremail import CreMail, ConfigError, EmailSendError

   try:
       sender = CreMail()
       result = sender.send_email(...)
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

方法9: 使用重试机制
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from cremail import CreMail

   sender = CreMail()
   result = sender.send_email(..., max_retries=3)

方法10: 使用异步发送
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

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

   asyncio.run(send_async_email())

方法11: 使用批量发送
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

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

   asyncio.run(batch_send_example())

API 参考
--------

类: CreMail
~~~~~~~~~~~

.. method:: CreMail.__init__(smtp_server=None, smtp_port=None, email=None, password=None, config_file="email_config.json", config_dict=None, config_provider=None, max_attachment_size=10485760, timeout=30, use_tls=True, use_ssl=False, provider_priority=False, from_display_name=None, smtp_client=None, password_callback=None, log_file=None)

   初始化邮件发送器。

   **参数:**

   - ``smtp_server`` (str, 可选): SMTP服务器地址
   - ``smtp_port`` (int, 可选): SMTP服务器端口
   - ``email`` (str, 可选): 发送者邮箱地址
   - ``password`` (str, 可选): 发送者邮箱密码或授权码
   - ``config_file`` (str): 配置文件路径 (默认: "email_config.json")
   - ``config_dict`` (dict, 可选): 配置字典
   - ``config_provider`` (ConfigProvider, 可选): 配置提供者
   - ``max_attachment_size`` (int): 最大附件大小 (默认: 10MB)
   - ``timeout`` (int): 连接超时时间 (默认: 30秒)
   - ``use_tls`` (bool): 是否使用TLS (默认: True)
   - ``use_ssl`` (bool): 是否使用SSL (默认: False)
   - ``provider_priority`` (bool): 是否优先使用config_provider (默认: False)
   - ``from_display_name`` (str, 可选): 发件人显示名称
   - ``smtp_client`` (SMTPClient, 可选): SMTP客户端实现
   - ``password_callback`` (callable, 可选): 密码获取回调函数
   - ``log_file`` (str, 可选): 日志文件路径，用于将日志写入文件。

.. method:: CreMail.send_email(recipient_email, subject, content, content_type="html", attachments=None, ignore_attachment_errors=False, max_retries=2, cc_recipients=None, bcc_recipients=None, reply_to=None, priority="normal", total_timeout=None)

   发送指定内容的自定义邮件。返回 ``SendResult`` 对象。

常规函数
~~~~~~~~

- ``send_email_with_config(recipient_email, subject, content, config_file="email_config.json", content_type="html", attachments=None, ignore_attachment_errors=False, max_retries=2, cc_recipients=None, bcc_recipients=None, reply_to=None, priority="normal", password_callback=None) -> SendResult``

- ``async_send_email(...) -> SendResult``

- ``render_template(template_file, data) -> str``

- ``generate_verification_code(length=6) -> str``

- ``generate_alphanumeric_verification_code(length=6) -> str``

- ``generate_letters_verification_code(length=6) -> str``

- ``generate_verification_code_unified(length=6, mode='digits') -> str``

自定义异常类
~~~~~~~~~~~~

- ``EmailSendError``
- ``ConfigError``
- ``SMTPConnectionError``
- ``AttachmentError``
- ``SizeLimitError``
- ``RateLimitError``
- ``ContentValidationError``

SendResult 类
~~~~~~~~~~~~~

属性：
- ``success`` (bool)
- ``message_id`` (str)
- ``error_detail`` (str)
- ``accepted_recipients`` (list)
- ``timestamp`` (float)
- ``exception`` (Exception)

配置方式
~~~~~~~~

支持多种配置方式，优先级如下：
1. 直接参数
2. config_dict
3. 环境变量
4. 配置文件

环境变量名称：
- ``SMTP_SERVER``
- ``SMTP_PORT``
- ``SMTP_EMAIL``
- ``SMTP_PASSWORD``

重试机制
~~~~~~~~

``send_email`` 方法支持 ``max_retries`` 参数，默认为 2 次重试，使用指数退避算法和随机抖动。

异步支持
~~~~~~~~

提供 ``async_send_email`` 异步函数和 ``batch_send`` 批量发送功能，需要安装 ``aiosmtplib`` 库。

模板渲染
~~~~~~~~

提供 ``render_template`` 函数，需要安装 ``jinja2`` 库。

日志记录
~~~~~~~~

该模块提供灵活的日志记录选项，具有用户友好的错误消息，包含故障排除建议。您可以通过两种方式配置日志记录：

1. 使用 ``CreMail(log_file='cremail.log')`` 写入文件。
2. 使用标准 ``logging`` 模块。

改进的日志系统提供清晰、可操作的错误消息和故障排除提示，帮助用户快速识别和解决常见问题，例如 SMTP 连接错误、认证错误、收件人错误、附件错误、配置错误等。

示例
----

.. code-block:: python

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

更多示例请参考 `GitHub 仓库 <https://github.com/MoCre-QiuMing/CreMail>`_。

许可证
------

本项目基于 MIT 许可证 - 详见 LICENSE 文件。

贡献
----

欢迎贡献！请随时提交 Pull Request。对于重大更改，请先开 issue 讨论您想要改变的内容。

问题反馈
--------

如果您遇到任何问题或对改进有建议，请在 GitHub 仓库中开 issue。