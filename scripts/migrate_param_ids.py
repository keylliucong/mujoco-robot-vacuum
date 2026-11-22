#!/usr/bin/env python3
"""历史入口：v1.8.1 两段键迁移已被 v1.8.4 三段键迁移取代。

保留此文件名只为兼容旧命令；实际逻辑在
`scripts/migrate_param_ids_callable.py`（可重跑、幂等、带改动清单）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from migrate_param_ids_callable import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
