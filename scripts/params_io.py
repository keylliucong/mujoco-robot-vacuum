"""参数外置：读取 params/<config_id>.json，把模型模板里的 ${id} 渲染成数值。

契约 v1.7 交付补充（仿真专家裁定）：
- `models/baseline.xml` 只描述结构与关节，所有物理数值以 `${id}` 占位；
- 数值的唯一住处是 `params/<config_id>.json`，每个值带六值来源标签；
- 模型头注释必须写 `model=baseline-cases; machine=<...>; parameter_source=<路径>`；
- `missing: true` 的参数是显式占位（如 z_cg），不得当实测或结论，等级推导封顶 mechanism。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

LABELS = {"本机实测", "图纸推算", "公开参考", "工程假设", "缺失", "待标定"}

PLACEHOLDER = re.compile(r"\$\{([A-Za-z0-9_.]+)\}")
HEADER = re.compile(
    r"model=(?P<model>[A-Za-z0-9_.-]+);\s*machine=(?P<machine>[A-Za-z0-9_.-]+);\s*"
    r"parameter_source=(?P<source>[^\s*;]+)"
)


class ParamError(RuntimeError):
    """参数缺失、标签非法或占位符未解析。"""


def parse_header(model_text):
    match = HEADER.search(model_text)
    if not match:
        raise ParamError(
            "模型头注释缺 `model=...; machine=...; parameter_source=...`（v1.7 交付补充）"
        )
    return match.groupdict()


def load_params(path):
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)
    for key in ("schema_version", "config_id", "machine", "params"):
        if key not in document:
            raise ParamError(f"{path} 缺键 {key}")
    prefix = f"{document['machine']}."
    keys = list(document["params"])
    prefixed = [param_id for param_id in keys if param_id.startswith(prefix)]
    if prefixed and len(prefixed) != len(keys):
        bare = [param_id for param_id in keys if not param_id.startswith(prefix)]
        raise ParamError(
            f"{path} 的 param_id 混用机型前缀与裸 id：裸 id {bare[:5]}；"
            f"整份参数集必须统一用 {prefix!r} 或统一裸 id"
        )
    for param_id, entry in document["params"].items():
        if "value" not in entry or "label" not in entry or "ref" not in entry:
            raise ParamError(f"{path} 的 {param_id} 缺 value/label/ref")
        if entry["label"] not in LABELS:
            raise ParamError(f"{param_id} 的 label 非法：{entry['label']}")
        if entry["label"] == "缺失" and not entry.get("missing"):
            raise ParamError(f"{param_id} 标【缺失】但未写 missing=true")
    return document


def format_number(value):
    number = float(value)
    if number == int(number) and abs(number) < 1e15:  # arithmetic
        return str(int(number))
    return repr(number)


def resolve_id(values, machine, config_id, param_id):
    """把模型模板里的裸占位符解析到 v1.8.4 的三段键。

    模型模板是跨机型共用的（`${mass.chassis}`），台账与 params 文件的键从
    v1.8.4 起是 `<machine>.<config_id>.<id>`。优先取裸 id（历史参数集），
    否则取当前机型/配置前缀；再退回 v1.8.1 的两段式，兼容尚未迁移的旧文件。
    不跨机型回退，避免把别的机型数值静默填进来。
    """
    if param_id in values:
        return param_id
    for prefixed in (
        f"{machine}.{config_id}.{param_id}",
        f"{machine}.{param_id}",
    ):
        if prefixed in values:
            return prefixed
    return None


def get_param(params_document, param_id):
    """按裸 id、三段键或旧两段键取参数条目，返回 (键, 条目)。"""
    values = params_document["params"]
    key = resolve_id(
        values,
        params_document["machine"],
        params_document["config_id"],
        param_id,
    )
    if key is None:
        raise ParamError(f"参数 {param_id} 在 {params_document['config_id']} 里不存在（不得静默填）")
    return key, values[key]


def render(model_text, params_document):
    values = params_document["params"]
    machine = params_document["machine"]
    config_id = params_document["config_id"]

    def replace(match):
        param_id = match.group(1)
        key = resolve_id(values, machine, config_id, param_id)
        if key is None:
            raise ParamError(f"模型占位 ${{{param_id}}} 在 params 文件里不存在（不得静默填）")
        return format_number(values[key]["value"])

    rendered = PLACEHOLDER.sub(replace, model_text)
    if "${" in rendered:
        raise ParamError("渲染后仍有未解析占位符")
    return rendered


def used_ids(model_text):
    return sorted(set(PLACEHOLDER.findall(model_text)))


def missing_ids(params_document):
    return sorted(
        param_id for param_id, entry in params_document["params"].items() if entry.get("missing")
    )


def load_and_render(model_path, params_path=None):
    """渲染模型模板。

    ``params_path`` 省略时按模型头 ``parameter_source`` 取（原行为）；给出时用它
    覆盖，用于同一模型跑多套参数（G2.5 敏感性扫描）。machine 必须与模型头一致。
    """
    model_path = Path(model_path)
    text = model_path.read_text(encoding="utf-8")
    header = parse_header(text)
    if params_path is None:
        params_path = (model_path.parent.parent / header["source"]).resolve()
    else:
        params_path = Path(params_path)
        if not params_path.is_absolute():
            params_path = (model_path.parent.parent / params_path).resolve()
    document = load_params(params_path)
    if document["machine"] != header["machine"]:
        raise ParamError(
            f"模型头 machine={header['machine']} 与 {params_path} 的 machine={document['machine']} 不一致"
        )
    return {
        "text": render(text, document),
        "template": text,
        "header": header,
        "params": document,
        "params_path": params_path,
    }
