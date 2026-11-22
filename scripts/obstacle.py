"""台阶注入器：把 scenario.obstacle 规范化后注入 worldbody（契约 S03）。

模型 XML 里不出现 step 几何；本模块是台阶几何的唯一产生点。注入后由
scripts/run_cases.py 对整段 XML 取 sha256 写进 run.json.scenario_xml_sha256。

只做几何注入与接触对生成，不 import mujoco（便于单独复核）。
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

PAIR_GEOMS = {
    "wheel_L": ("wheel_L_tire",),
    "wheel_R": ("wheel_R_tire",),
    "chassis": ("chassis_body",),
    "caster": ("caster_ball",),
    "floor": ("floor_plane",),
    "step": ("step", "step_edge"),
}


class ObstacleError(ValueError):
    """台阶参数或模型拓扑不合法。"""


def pair_geom_names(key, obstacle_shape):
    a, _, b = key.partition("--")
    names_a = list(PAIR_GEOMS[a])
    names_b = list(PAIR_GEOMS[b])
    if obstacle_shape != "step":
        names_b = [n for n in names_b if not n.startswith("step")]
    return names_a, names_b


def _add_step(root, config, chassis_front_m, defaults):
    obstacle = config["scenario"]["obstacle"]
    half_width = defaults["obstacle_half_width_m"]
    height = obstacle["height_m"]
    radius = obstacle["edge_radius_m"]
    width = obstacle["top_width_m"]
    heading = math.radians(config["scenario"]["heading_deg"])
    x_edge = chassis_front_m + config["scenario"]["approach"]["start_distance_m"]
    worldbody = root.find("worldbody")
    if worldbody is None:
        raise ObstacleError("模型缺 worldbody")
    quat = f"{math.cos(heading / 2)} 0 0 {math.sin(heading / 2)}"
    body = ET.SubElement(
        worldbody, "body", {"name": "obstacle", "pos": f"{x_edge} 0 0", "quat": quat}
    )
    if obstacle["shape"] == "box":
        box_h = height - radius
        if box_h <= 0:
            raise ObstacleError("edge_radius_m 必须小于 height_m")
        ET.SubElement(
            body,
            "geom",
            {
                "name": "step",
                "type": "box",
                "size": f"{width / 2} {half_width} {box_h / 2}",
                "pos": f"{width / 2} 0 {box_h / 2}",
                "material": "step",
            },
        )
        if radius > 0:
            ET.SubElement(
                body,
                "geom",
                {
                    "name": "step_edge",
                    "type": "cylinder",
                    "size": f"{radius} {half_width}",
                    "pos": f"{radius} 0 {height - radius}",
                    "quat": "0.7071067811865476 0.7071067811865476 0 0",
                    "material": "step",
                },
            )
    else:
        ET.SubElement(
            body,
            "geom",
            {
                "name": "step",
                "type": "cylinder",
                "size": f"{height / 2} {half_width}",
                "pos": f"{height / 2} 0 {height / 2}",
                "quat": "0.7071067811865476 0.7071067811865476 0 0",
                "material": "step",
            },
        )


def inject(model_text, config, chassis_front_m, defaults):
    """返回注入台阶与接触对后的 XML 文本。"""
    root = ET.fromstring(model_text)
    kind = config["scenario"]["kind"]
    if kind == "step":
        _add_step(root, config, chassis_front_m, defaults)

    geom_names = {geom.get("name") for geom in root.iter("geom")}
    # pair 元素不继承 <default><geom>，只继承 <default><pair>；把模型 geom 默认的
    # solref/solimp 显式带到注入的 pair 上，避免悄悄退回引擎默认值（S15 无静默降级）。
    default_geom = root.find("./default/geom")
    pair_contact_attrs = {}
    if default_geom is not None:
        for attr in ("solref", "solimp"):
            value = default_geom.get(attr)
            if value:
                pair_contact_attrs[attr] = value
    pair_elements = []
    for key, spec in config["environment"]["pairs"].items():
        names_a, names_b = pair_geom_names(key, kind)
        if not any(name in geom_names for name in names_a):
            raise ObstacleError(f"接触对 {key} 的侧 {names_a} 在模型里不存在")
        friction = [float(v) for v in spec["friction"]]
        if len(friction) != 5:
            raise ObstacleError(
                f"{key}.friction 必须是 5 分量 [slide1, slide2, spin, roll1, roll2]；"
                f"实际 {len(friction)} 个，禁止用单值/3 分量让其余分量回落默认"
            )
        if friction[0] != friction[1]:
            raise ObstacleError(
                f"{key}.friction 非各向同性：slide1={friction[0]} slide2={friction[1]}"
            )
        for name_a in names_a:
            for name_b in names_b:
                if name_a not in geom_names or name_b not in geom_names:
                    continue
                attrs = {
                    "geom1": name_a,
                    "geom2": name_b,
                    "condim": str(spec["condim"]),
                    "friction": " ".join(str(v) for v in friction),
                }
                attrs.update(pair_contact_attrs)
                pair_elements.append(attrs)
    if pair_elements:
        contact = root.find("contact")
        if contact is None:
            contact = ET.SubElement(root, "contact")
        for attrs in pair_elements:
            ET.SubElement(contact, "pair", attrs)
    return ET.tostring(root, encoding="unicode")
