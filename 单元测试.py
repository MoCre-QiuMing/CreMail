#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
本脚本为【本地离线】测试：通过 mock 的 SMTP 客户端替代真实发送，全程【不会】
向任何真实邮箱外发邮件，也【不需要】 email_config.json 配置文件。
验证范围：配置加载、纯文本/HTML/附件/忽略附件错误/CC-BCC/异步/批量/模板/
默认发送者/验证码/快捷函数，以及 2.2.1 新增的可靠性修复（去重、幂等 Message-ID、
连接断开不盲发、附件超限异常分类、限流、工具函数导出、版本号）。

运行：python 单元测试.py   （需在 2.2.1 目录内，或本目录包含 cremail 包）
"""

import os
import sys
import time
import json
import tempfile
import asyncio
import shutil
import smtplib
from pathlib import Path
from unittest import mock

# ========== 使用您的库 ==========
try:
    from cremail import (
        CreMail,
        SendResult,
        AioSMTPLibClient,
        ConfigError,
        EmailSendError,
        AttachmentError,
        SizeLimitError,
        RateLimitError,
        generate_verification_code,
        generate_alphanumeric_verification_code,
        generate_letters_verification_code,
        generate_verification_code_unified,
        render_template,
        send_email_with_config,
        async_send_email,
        get_default_sender,
        send_email_with_default_sender,
        validate_email_address,
        validate_email_list,
        format_email_with_name,
        VERIFICATION_CODE_DIGITS,
        VERIFICATION_CODE_LETTERS,
        VERIFICATION_CODE_MIX,
    )
    import cremail as cremail_pkg
except ImportError as e:
    print(f"❌ 导入 cremail 失败: {e}")
    print("请确认在 2.2.1 目录下运行，或设置 PYTHONPATH 指向 2.2.1 目录。")
    sys.exit(1)

# ========== 假配置与 mock 客户端 ==========
FAKE_CFG = dict(smtp_server="smtp.test.com", smtp_port=587,
                email="sender@test.com", password="secret")

class FakeClient:
    """mock SMTP 客户端：记录调用参数，可编程抛错；绝不触碰真实 SMTP。"""
    def __init__(self, result=None, exc=None, async_exc=None):
        self.result = result if result is not None else {}
        self.exc = exc
        self.async_exc = async_exc
        self.calls = []
    def connect_and_send(self, message, **kw):
        self.calls.append((message, kw))
        if self.exc:
            raise self.exc
        return self.result
    async def async_send_message(self, message, **kw):
        self.calls.append((message, kw))
        if self.async_exc:
            raise self.async_exc
        return self.result

def make_sender(smtp_client=None, **kw):
    """构造测试用 sender（本地离线），默认关闭发送间隔限流。"""
    cfg = dict(FAKE_CFG)
    cfg.update({k: v for k, v in kw.items() if k in ("smtp_server", "smtp_port", "email", "password")})
    s = CreMail(config_dict=cfg, smtp_client=smtp_client or FakeClient())
    s.rate_limit_delay = 0
    return s

# ========== 测试结果收集 ==========
class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = False
        self.message = ""
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} - {self.name}: {self.message}"

results = []

def run_test(name, func):
    tr = TestResult(name)
    try:
        func()
        tr.passed = True
        tr.message = "OK"
    except AssertionError as e:
        tr.passed = False
        tr.message = str(e)
    except Exception as e:
        tr.passed = False
        tr.message = f"ERROR: {e}"
    results.append(tr)
    print(tr)

# ========== 测试辅助 ==========
temp_dir = tempfile.mkdtemp(prefix="cremail_offline_test_")
print(f"📁 临时测试目录: {temp_dir}")

attachment_txt = Path(temp_dir) / "test_attach.txt"
attachment_txt.write_text("这是测试附件的内容", encoding="utf-8")
attachment_bin = Path(temp_dir) / "test_bin.bin"
attachment_bin.write_bytes(b'\x00\x01\x02\x03\x04')
attachments = [str(attachment_txt), str(attachment_bin)]

template_file = Path(temp_dir) / "template.html"
template_file.write_text("""
<!DOCTYPE html>
<html><body>
    <h1>Hello {{ name }}!</h1>
    <p>这是通过模板渲染的邮件，当前时间：{{ now }}</p>
</body></html>
""", encoding="utf-8")

missing_attach = Path(temp_dir) / "missing.txt"  # 故意不创建

def cleanup():
    shutil.rmtree(temp_dir, ignore_errors=True)

# ========== 测试用例（全部本地离线） ==========

# 1. 配置加载
def test_config_loading():
    s = make_sender()
    assert s.smtp_server, "SMTP服务器未配置"
    assert s.smtp_port, "SMTP端口未配置"
    assert s.email, "发件人邮箱未配置"
    assert s.password, "密码未配置"
    # 缺失配置应抛 ConfigError（2.2.1 仍保持）
    try:
        CreMail(config_dict={"smtp_server": "x"}, config_file=None)
        raise AssertionError("缺失配置未抛 ConfigError")
    except ConfigError:
        pass

# 2. 纯文本发送（mock）
def test_plain_text():
    fake = FakeClient()
    s = make_sender(fake)
    r = s.send_email("user@example.com", "纯文本测试", "离线纯文本", content_type="plain")
    assert r.success, f"发送失败: {r.error_detail}"
    assert r.message_id.startswith("<") and "@" in r.message_id, "message_id 应为真实 Message-ID 格式"
    # 未触碰真实 SMTP
    assert len(fake.calls) == 1

# 3. HTML 发送（mock）
def test_html_email():
    fake = FakeClient()
    s = make_sender(fake)
    r = s.send_email("user@example.com", "HTML测试", "<h2>离线HTML</h2>", content_type="html")
    assert r.success

# 4. 带附件（mock）
def test_attachments():
    fake = FakeClient()
    s = make_sender(fake)
    r = s.send_email("user@example.com", "附件测试", "含附件", attachments=attachments)
    assert r.success, f"失败: {r.error_detail}"

# 5. 忽略附件错误（mock）
def test_ignore_attachment_errors():
    fake = FakeClient()
    s = make_sender(fake)
    r = s.send_email("user@example.com", "附件错误忽略", "忽略缺失附件",
                     attachments=attachments + [str(missing_attach)],
                     ignore_attachment_errors=True)
    assert r.success

# 6. CC/BCC + 去重（mock）
def test_cc_bcc_dedup():
    fake = FakeClient()
    s = make_sender(fake)
    r = s.send_email("user@example.com", "CC/BCC测试", "cc/bcc",
                     cc_recipients=["cc@example.com", "user@example.com"],
                     bcc_recipients=["bcc@example.com"])
    assert r.success
    recips = r.accepted_recipients
    assert len(recips) == len(set(recips)), f"收件人未去重: {recips}"
    assert "cc@example.com" in recips and "bcc@example.com" in recips

# 7. 异步发送（mock）
def test_async():
    # 通过模块级 async_send_email 验证（mock 掉底层异步发送方法，不真实外发）
    import importlib
    cm = importlib.import_module("cremail.CreMail")
    with mock.patch.object(cm.CreMail, "_async_send_individual_email") as m:
        m.return_value = SendResult(success=True, message_id="<a@b>")
        async def run():
            return await async_send_email("user@example.com", "异步发送测试", "离线异步",
                                          config_dict=FAKE_CFG, content_type="html")
        r = asyncio.run(run())
    assert r.success

# 8. 批量发送（mock 异步）
def test_batch():
    fake = FakeClient(result={})
    s = make_sender(fake)
    s.rate_limit_delay = 0
    emails = [
        {"recipient_email": "a@example.com", "subject": "批量1", "content": "第1封", "content_type": "plain"},
        {"recipient_email": "b@example.com", "subject": "批量2", "content": "第2封", "content_type": "plain"},
    ]
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    try:
        rs = loop.run_until_complete(s.batch_send(emails, batch_size=2, max_concurrent=2))
    finally:
        loop.close()
    assert len(rs) == 2 and all(r.success for r in rs)

# 9. 模板渲染
def test_template():
    data = {"name": "CreMail用户", "now": time.strftime("%Y-%m-%d %H:%M:%S")}
    content = render_template(str(template_file), data)
    assert "CreMail用户" in content, "模板渲染结果未包含数据"

# 10. 全局默认发送者（mock 发送）
def test_default_sender():
    # 单例
    import importlib
    cm = importlib.import_module("cremail.CreMail")
    with mock.patch.object(cm, "_default_sender", None):
        s1 = get_default_sender(config_dict=FAKE_CFG)
        s2 = get_default_sender(config_dict=FAKE_CFG)
        assert s1 is s2, "get_default_sender 未返回同一实例"
    # 通过默认发送者发送（mock，不真实外发）
    import importlib
    cm = importlib.import_module("cremail.CreMail")
    with mock.patch.object(cm, "CreMail") as M:
        inst = M.return_value
        inst.send_email.return_value = SendResult(success=True, message_id="<d@x>")
        r = send_email_with_default_sender(recipient_email="u@example.com",
                                           subject="默认发送者", content="离线",
                                           content_type="plain")
    assert r.success

# 11. 验证码生成
def test_verification_codes():
    d = generate_verification_code(6); l = generate_letters_verification_code(4)
    m = generate_alphanumeric_verification_code(8)
    u = generate_verification_code_unified(6, mode=VERIFICATION_CODE_MIX)
    assert len(d) == 6 and d.isdigit()
    assert len(l) == 4 and l.isalpha()
    assert len(m) == 8 and any(c.isalnum() for c in m)
    assert len(u) == 6

# 12. send_email_with_config 快捷函数（mock）
def test_send_with_config():
    import importlib
    cm = importlib.import_module("cremail.CreMail")
    with mock.patch.object(cm, "CreMail") as M:
        inst = M.return_value
        inst.send_email.return_value = SendResult(success=True, message_id="<c@x>")
        r = send_email_with_config(recipient_email="u@example.com", subject="快捷",
                                   content="离线", config_file=None,
                                   content_type="plain", total_timeout=10)
    assert r.success
    assert inst.send_email.called

# ===== 2.2.1 新增可靠性/API 验证 =====

# 13. 收件人去重（_collect_recipients 行为）
def test_recipient_dedup_build():
    from cremail.CreMail import _collect_recipients
    got = _collect_recipients("a@example.com", cc=["b@example.com", "a@example.com"],
                              bcc=["c@example.com", "b@example.com"])
    assert got == ["a@example.com", "b@example.com", "c@example.com"], f"未去重: {got}"

# 14. 附件超限：SizeLimitError 独立抛出且不触碰 SMTP
def test_attachment_sizelimit():
    fake = FakeClient()
    s = make_sender(fake)
    s.max_attachment_size = 10
    big = Path(temp_dir) / "big.bin"; big.write_bytes(b"x" * 100)
    try:
        s.send_email("u@example.com", "超限", "内容", attachments=[str(big)])
        raise AssertionError("超限附件未抛 SizeLimitError")
    except SizeLimitError:
        pass
    assert len(fake.calls) == 0, "超限附件不应触发 SMTP"

# 15. 连接断开不盲发（SMTPServerDisconnected 不重试）
def test_disconnect_not_retried():
    fake = FakeClient(result=None, exc=smtplib.SMTPServerDisconnected("closed"))
    s = make_sender(fake)
    r = s.send_email("u@example.com", "断开", "内容", max_retries=3)
    assert not r.success
    assert len(fake.calls) == 1, "连接断开不应无脑重试（避免重复投递）"
    assert "MAY already be delivered" in r.error_detail

# 16. 重试幂等：重试期间 Message-ID 不变
def test_retry_same_msgid():
    calls = []
    class Flaky:
        def __init__(self): self.n = 0
        def connect_and_send(self, message, **kw):
            calls.append(message["Message-ID"]); self.n += 1
            if self.n == 1:
                raise RuntimeError("transient")
            return {}
    s = make_sender(Flaky())
    r = s.send_email("u@example.com", "重试", "内容", max_retries=2)
    assert r.success
    assert len(set(calls)) == 1, f"重试期间 Message-ID 不一致: {calls}"

# 17. 限流：单日上限抛 RateLimitError
def test_daily_limit():
    s = make_sender(FakeClient())
    s.daily_send_limit = 1
    assert s.send_email("u@example.com", "限流", "内容").success
    try:
        s.send_email("u@example.com", "限流2", "内容")
        raise AssertionError("未抛 RateLimitError")
    except RateLimitError:
        pass

# 18. 工具函数顶层导出
def test_validate_exported():
    assert callable(validate_email_address) and callable(validate_email_list)
    assert callable(format_email_with_name)
    assert validate_email_address("a@b.com") and not validate_email_address("bad-addr")

# 19. 版本号
def test_version():
    assert cremail_pkg.__version__ == "2.2.1", f"版本应为 2.2.1，实际 {cremail_pkg.__version__}"

# 20. 异步参数回归（真实触达 aiosmtplib 构造，验证 use_tls 而非 use_ssl）
def test_async_params():
    import importlib
    from email.mime.text import MIMEText
    cm = importlib.import_module("cremail.CreMail")
    msg = MIMEText("hi")
    msg['To'] = "user@example.com"
    msg['Cc'] = ""
    with mock.patch.object(cm.aiosmtplib, "SMTP") as MockSMTP:
        inst = mock.AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = False
        MockSMTP.return_value = inst
        client = AioSMTPLibClient()
        # use_ssl=False → use_tls=False（STARTTLS 语义）
        asyncio.run(client.async_send_message(msg, hostname="smtp.test.com", port=587,
                                              username="u", password="p", use_ssl=False,
                                              recipients=["user@example.com"]))
        kw = MockSMTP.call_args.kwargs
        assert "use_ssl" not in kw, f"不应传 use_ssl 参数: {kw}"
        assert kw.get("use_tls") is False, f"use_ssl=False 应映射为 use_tls=False: {kw}"
        # use_ssl=True → use_tls=True（SSL 直连，465）
        asyncio.run(client.async_send_message(msg, hostname="smtp.test.com", port=465,
                                              username="u", password="p", use_ssl=True,
                                              recipients=["user@example.com"]))
        kw = MockSMTP.call_args.kwargs
        assert "use_ssl" not in kw, f"不应传 use_ssl 参数: {kw}"
        assert kw.get("use_tls") is True, f"use_ssl=True 应映射为 use_tls=True: {kw}"

# ========== 执行测试 ==========
def main():
    print(f"\n🚀 开始本地离线测试 CreMail（不发送任何真实邮件，无需配置文件）\n")

    tests = [
        ("配置加载", test_config_loading),
        ("纯文本邮件", test_plain_text),
        ("HTML邮件", test_html_email),
        ("带附件邮件", test_attachments),
        ("忽略附件错误", test_ignore_attachment_errors),
        ("CC/BCC + 去重", test_cc_bcc_dedup),
        ("异步发送", test_async),
        ("批量发送", test_batch),
        ("模板渲染", test_template),
        ("全局默认发送者", test_default_sender),
        ("验证码生成", test_verification_codes),
        ("快捷函数发送", test_send_with_config),
        ("收件人去重(构建)", test_recipient_dedup_build),
        ("附件超限异常分类", test_attachment_sizelimit),
        ("连接断开不盲发", test_disconnect_not_retried),
        ("重试幂等Message-ID", test_retry_same_msgid),
        ("内置限流", test_daily_limit),
        ("工具函数顶层导出", test_validate_exported),
        ("版本号2.2.1", test_version),
        ("异步参数回归", test_async_params),
    ]
    try:
        for name, fn in tests:
            run_test(name, fn)
    except Exception as e:
        print(f"\n⚠️ 测试过程中发生未预期异常: {e}")
    finally:
        cleanup()
        print("\n" + "=" * 60)
        print("📊 测试结果汇总（本地离线，未发送任何真实邮件）:")
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        for r in results:
            print(r)
        print(f"\n总计: {passed}/{total} 项测试通过")
        if passed == total:
            print("🎉 所有测试通过！")
        else:
            print("⚠️ 部分测试失败，请检查错误信息。")
        print("=" * 60)
        return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
