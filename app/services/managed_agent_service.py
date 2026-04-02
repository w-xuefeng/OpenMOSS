"""
managed_agent 兼容入口。

新代码应直接从 `app.services.managed_agent` 包导入。
这里暂时保留，避免一次性打断旧引用。
"""

from app.services.managed_agent import *  # noqa: F401,F403
