"""Check the intake format documented in docs/机型包规范.md."""

import argparse
import json
import re
import sys
from pathlib import Path
from xml.parsers import expat


ROOT_FIELDS = (
    "schema_version", "machine_id", "payload_state", "config_id",
    "base_link", "drive_wheels", "capabilities", "support_points", "assembly",
)
MASS_FIELDS = (
    "mass_kg", "com_x_m", "com_y_m", "com_z_m",
    "ixx_kg_m2", "iyy_kg_m2", "izz_kg_m2",
    "ixy_kg_m2", "ixz_kg_m2", "iyz_kg_m2",
)
SOURCES = ("measured", "datasheet", "cad", "assumed", "missing")


def index_json(content, report):
    """Index lines by field path after the standard JSON parser checks syntax."""
    tokens = iter(re.finditer(r'"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^\s{}\[\]:,"]+', content))
    lines = {}
    previous_offset = 0
    line = 1

    def read_token():
        nonlocal line, previous_offset
        token = next(tokens)
        line += content.count("\n", previous_offset, token.start())
        previous_offset = token.start()
        return token.group(), line

    def walk(token, path, field_line):
        lines[path] = field_line
        if token == "{":
            key, key_line = read_token()
            while key != "}":
                child = f"{path}.{json.loads(key)}"
                if child in lines:
                    report(key_line, child, "哪里可能填错", "字段重复，请只保留一处。")
                read_token()  # colon
                value, _ = read_token()
                walk(value, child, key_line)
                delimiter, _ = read_token()
                if delimiter == "}":
                    break
                key, key_line = read_token()
        elif token == "[":
            value, value_line = read_token()
            index = 0
            while value != "]":
                walk(value, f"{path}[{index}]", value_line)
                index += 1
                delimiter, _ = read_token()
                if delimiter == "]":
                    break
                value, value_line = read_token()

    token, root_line = read_token()
    walk(token, "$", root_line)
    return lines


def read_urdf(path, report):
    parser = expat.ParserCreate()
    links, joints = set(), {}
    stack = []
    current_joint = None

    def start(tag, attrs):
        nonlocal current_joint
        stack.append(tag)
        line = parser.CurrentLineNumber
        if len(stack) == 1 and tag != "robot":
            report(line, tag, "哪里可能填错", "根元素应为 <robot>，请导出 URDF。")
        elif stack in (["robot", "link"], ["robot", "joint"]):
            name = attrs.get("name", "")
            known = links if tag == "link" else joints
            current_joint = None
            if not name.strip() or name in known:
                report(line, f"{tag}.{name}", "哪里可能填错", "请填写非空且唯一的 name。")
            elif tag == "link":
                links.add(name)
            else:
                joints[name] = {"type": attrs.get("type"), "line": line}
                current_joint = name
        elif stack in (["robot", "joint", "parent"], ["robot", "joint", "child"]):
            if current_joint is not None:
                joint = joints[current_joint]
                if tag in joint:
                    report(line, f"joint.{current_joint}.{tag}", "哪里可能填错", "请只保留一个该元素。")
                joint[tag] = (attrs.get("link"), line)

    parser.StartElementHandler = start
    parser.EndElementHandler = lambda tag: stack.pop()
    try:
        parser.Parse(path.read_bytes(), True)
    except (OSError, LookupError, expat.ExpatError) as exc:
        report(getattr(exc, "lineno", 1), "robot", "哪里可能填错", f"无法读取 URDF，请检查文件路径和 XML。{exc}")
        return None
    for name, joint in joints.items():
        for end in ("parent", "child"):
            link, line = joint.get(end, (None, joint["line"]))
            if link not in links:
                report(line, f"joint.{name}.{end}.link", "哪里可能填错", "请填写 URDF 中已有的 link 名称。")
    return links, joints


class PackCheck:
    def __init__(self, path, lines, links, joints):
        self.path, self.lines = path, lines
        self.links, self.joints = links, joints
        self.errors = 0
        self.missing_values = 0

    def issue(self, field, message, category="哪里可能填错", *, advisory=False):
        parent = field.rsplit(".", 1)[0]
        line = self.lines.get(field, self.lines.get(parent, self.lines["$"]))
        print(f"{self.path}:{line} {field} [{category}] {message}")
        if not advisory:
            self.errors += 1

    def fields(self, obj, field, required, optional=()):
        if not isinstance(obj, dict):
            self.issue(field, "请用一对大括号填写这一组。")
            return False
        for name in required:
            if name not in obj:
                self.issue(f"{field}.{name}", "请从模板补回此字段。", "缺什么")
        for name in sorted(obj.keys() - set(required) - set(optional)):
            self.issue(f"{field}.{name}", "模板中没有此字段，请核对拼写。")
        return True

    def name(self, value, field, known=None):
        if not isinstance(value, str) or not value.strip():
            self.issue(field, '请填双引号括起的非空名称。')
            return False
        if known is not None and value not in known:
            self.issue(field, f"URDF 中找不到 {value!r}，请复制对应的 name。")
            return False
        return True

    def quantity(self, obj, field, *, positive=False, length_hint=False, optional_value=False):
        if not self.fields(obj, field, ("value", "source", "note")):
            return
        source, value = obj.get("source"), obj.get("value")
        if "source" in obj and source not in SOURCES:
            self.issue(f"{field}.source", "请填写以下一项：" + " / ".join(SOURCES))
        if "note" in obj:
            self.name(obj["note"], f"{field}.note")
        if "value" not in obj:
            return
        if value is None:
            if source != "missing":
                self.issue(f"{field}.source", 'value 是 null 时，请填 "missing"，并在 note 说明缺项。')
            elif not optional_value:
                self.missing_values += 1
                self.issue(f"{field}.value", "已登记缺值，使用该数计算前请按 note 补数据。", "缺什么", advisory=True)
            return
        if source == "missing":
            self.issue(f"{field}.value", 'source 是 "missing" 时，请填 null，或更正实际来源。')
        if type(value) not in (int, float) or not abs(value) <= sys.float_info.max:
            self.issue(f"{field}.value", "请填写有限数字（不加引号或单位），缺值填 null。")
        elif positive and value <= 0:
            self.issue(f"{field}.value", "请填写大于 0 的数，缺值填 null。")
        elif length_hint and value >= 1:
            self.issue(f"{field}.value", "数值达到 1 m，请确认从图纸抄录时没有把 mm 当 m。", advisory=True)

    def mass_properties(self, obj, field):
        if self.fields(obj, field, MASS_FIELDS):
            for key in MASS_FIELDS:
                if key in obj:
                    self.quantity(obj[key], f"{field}.{key}", positive=key == "mass_kg" or key[:3] in ("ixx", "iyy", "izz"))

    def drive_wheels(self, wheels, field):
        if not isinstance(wheels, list):
            self.issue(field, "请用方括号列出驱动轮。")
            return set()
        seen_links, seen_joints = set(), set()
        required = ("link", "joint", "radius_m", "torque_limit_nm", "speed_limit_radps")
        for index, wheel in enumerate(wheels):
            item = f"{field}[{index}]"
            if not self.fields(wheel, item, required):
                continue
            for key, known, seen in (("link", self.links, seen_links), ("joint", self.joints, seen_joints)):
                if key in wheel and self.name(wheel[key], f"{item}.{key}", known):
                    if wheel[key] in seen:
                        self.issue(f"{item}.{key}", "重复引用，请为每个驱动轮使用自己的名称。")
                    seen.add(wheel[key])
            joint_name = wheel.get("joint")
            joint = self.joints.get(joint_name) if isinstance(joint_name, str) else None
            if joint is not None:
                if joint["type"] not in ("continuous", "revolute"):
                    self.issue(f"{item}.joint", "请选择 URDF 中类型为 continuous 或 revolute 的转轴。")
                child, _ = joint.get("child", (None, None))
                if child is not None and "link" in wheel and wheel["link"] != child:
                    self.issue(f"{item}.link", f"该转轴的 child 是 {child!r}，请核对轮体与转轴是否配对。")
            for key in required[2:]:
                if key in wheel:
                    self.quantity(wheel[key], f"{item}.{key}", positive=True, length_hint=key == "radius_m")
        return seen_joints

    def capabilities(self, obj):
        field = "$.capabilities"
        if not isinstance(obj, dict):
            self.issue(field, "请用一对大括号填写能力名称和声明。")
            return None
        if "suspension" not in obj:
            self.issue(f"{field}.suspension", "请声明机型是否有悬挂。", "缺什么")
        for key, enabled in obj.items():
            if not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", key) or key.startswith("has_"):
                self.issue(f"{field}.{key}", "请用小写英文名称，下划线分词，去掉 has_ 前缀。")
            if type(enabled) is not bool:
                self.issue(f"{field}.{key}", "请填 true（有）或 false（无），不加引号。")
        return obj.get("suspension")

    def support_points(self, entries):
        field = "$.support_points"
        if not isinstance(entries, list):
            self.issue(field, "请用方括号列出从动支撑点。")
            return
        for index, entry in enumerate(entries):
            item = f"{field}[{index}]"
            if not self.fields(entry, item, ("link", "type", "radius_m", "position")):
                continue
            if "link" in entry:
                self.name(entry["link"], f"{item}.link", self.links)
            kind = entry.get("type")
            if "type" in entry and kind not in ("caster", "skid"):
                self.issue(f"{item}.type", '请填 "caster"（从动轮）或 "skid"（滑橇）。')
            if "radius_m" in entry:
                self.quantity(entry["radius_m"], f"{item}.radius_m", positive=True,
                              length_hint=True, optional_value=kind == "skid")
            if "position" not in entry or entry["position"] == "urdf_link_origin":
                continue
            position = entry["position"]
            position_field = f"{item}.position"
            if not isinstance(position, dict):
                self.issue(position_field, '请填 "urdf_link_origin"，或填写 B 系三个坐标。')
                continue
            axes = ("x_m", "y_m", "z_m")
            self.fields(position, position_field, axes)
            for axis in axes:
                if axis in position:
                    self.quantity(position[axis], f"{position_field}.{axis}")

    def suspension(self, obj, drive_joints, exists):
        field = "$.suspension_joints"
        if "suspension_joints" not in obj:
            if exists is True:
                self.issue(field, "有悬挂时请从模板补回悬挂关节清单。", "缺什么")
            return
        entries = obj["suspension_joints"]
        if not isinstance(entries, list):
            self.issue(field, "请用方括号列出悬挂关节。")
            return
        if exists is False and entries:
            self.issue(field, "无悬挂时请删除此字段或留空清单 []。")
        if exists is True and not entries:
            self.issue(field, "有悬挂时请至少列出一个悬挂关节。", "缺什么")
        seen = set()
        for index, entry in enumerate(entries):
            item = f"{field}[{index}]"
            if not self.fields(entry, item, ("joint", "travel_m")):
                continue
            if "joint" in entry and self.name(entry["joint"], f"{item}.joint", self.joints):
                name = entry["joint"]
                if name in drive_joints or name in seen or self.joints[name]["type"] not in ("continuous", "revolute", "prismatic"):
                    self.issue(f"{item}.joint", "请选择一个尚未列出的独立悬挂铰或滑移关节。")
                seen.add(name)
            if "travel_m" in entry:
                self.quantity(entry["travel_m"], f"{item}.travel_m", positive=True, length_hint=True)

    def check(self, obj):
        if not self.fields(obj, "$", ROOT_FIELDS, ("suspension_joints", "payload_addition")):
            return
        if "schema_version" in obj and obj["schema_version"] != "1.0":
            self.issue("$.schema_version", '请保留模板中的 "1.0"。')
        for key in ("machine_id", "config_id", "base_link"):
            if key in obj:
                self.name(obj[key], f"$.{key}", self.links if key == "base_link" else None)
        state = obj.get("payload_state")
        if "payload_state" in obj and state not in ("empty", "loaded"):
            self.issue("$.payload_state", '请填 "empty"（空载）或 "loaded"（加了载荷）。')
        if "payload_addition" in obj:
            if state == "empty":
                self.issue("$.payload_addition", "空载请删除这组附加载荷数据。")
            self.mass_properties(obj["payload_addition"], "$.payload_addition")
        elif state == "loaded":
            self.issue("$.payload_addition", "有载荷时请从模板补回附加载荷数据，未知数填 null。", "缺什么")
        if "assembly" in obj:
            self.mass_properties(obj["assembly"], "$.assembly")
        drive_joints = set()
        if "drive_wheels" in obj:
            drive_joints = self.drive_wheels(obj["drive_wheels"], "$.drive_wheels")
        if "support_points" in obj:
            self.support_points(obj["support_points"])
        has_suspension = self.capabilities(obj["capabilities"]) if "capabilities" in obj else None
        self.suspension(obj, drive_joints, has_suspension)


def main():
    cli = argparse.ArgumentParser(description="校验一个 URDF 文件与一个机型参数 JSON。")
    cli.add_argument("urdf", type=Path)
    cli.add_argument("params", type=Path)
    args = cli.parse_args()
    errors = []

    def report(path, line, field, category, message):
        errors.append(f"{path}:{line} {field} [{category}] {message}")

    for path, suffix in ((args.urdf, ".urdf"), (args.params, ".json")):
        if path.suffix.lower() != suffix:
            report(path, 1, "$", "哪里可能填错", f"请选择 {suffix} 文件。")

    urdf = read_urdf(args.urdf, lambda *details: report(args.urdf, *details))
    try:
        content = args.params.read_text(encoding="utf-8-sig")
        obj = json.loads(content)
        lines = index_json(content, lambda *details: report(args.params, *details))
    except json.JSONDecodeError as exc:
        report(args.params, exc.lineno, "$", "哪里可能填错",
               f"JSON 第 {exc.colno} 列附近有语法错误，请核对逗号、双引号和括号。{exc.msg}")
    except (OSError, UnicodeError, RecursionError, ValueError) as exc:
        report(args.params, 1, "$", "哪里可能填错", f"请检查文件路径并保存为 UTF-8 JSON。{exc}")

    if errors:
        print("\n".join(errors))
        print("未通过：请修正提示中的项目后重跑。")
        return 1

    result = PackCheck(args.params, lines, *urdf)
    result.check(obj)
    if result.errors:
        print("未通过：请修正提示中的项目后重跑。")
        return 1
    print(f"通过：机型包格式检查通过，已登记 {result.missing_values} 项缺值。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
