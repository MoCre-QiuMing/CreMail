# -*- coding: utf-8 -*-
"""
注：
本文件是 `cremail` 包内 `CreMail.py` 的薄包装，用于保持"直接运行本脚本"的
便利性，同时避免与包内实现重复维护（2.x 早期版本存在双份实现漂移问题）。
实际实现见 `cremail/CreMail.py`。

用法：
    python CreMail.py            # 模块就绪检查
    from CreMail import CreMail   # 等价于 from cremail import CreMail
"""

from cremail.CreMail import * 
from cremail.CreMail import CreMail, logger  

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    try:
        email_sender = CreMail()
        logger.info("CreMail module is ready to use")
    except Exception as e:
        logger.error(f"Failed to initialize CreMail: {str(e)}")
