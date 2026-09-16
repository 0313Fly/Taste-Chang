"""根据店名关键词自动打标。"""

from __future__ import annotations

# (标签, 关键词列表) — 按优先级大致从具体到宽泛
TAG_RULES: list[tuple[str, list[str]]] = [
    ("火锅", ["火锅", "涮羊肉", "串串", "烙锅", "冷锅", "酸汤"]),
    ("烤肉烧烤", ["烤肉", "烧烤", "烤串", "烧鸟", "自助烧烤"]),
    ("烤鱼海鲜", ["烤鱼", "河豚", "麻椒鱼", "冷锅鱼", "仙鱼", "鱼酷", "鱼摆摆"]),
    ("麻辣香锅", ["麻辣香锅", "麻辣烫", "川味", "螺蛳粉"]),
    ("面食小吃", ["面", "馄饨", "粉丝", "拉面", "小吃", "鸭脖", "煲仔", "拌饭"]),
    ("砂锅", ["砂锅"]),
    ("自助", ["自助"]),
    ("常州菜", ["常州菜", "地锅鸡"]),
    ("地方菜", ["江西", "台湾", "东北", "贵州", "北京", "苏式", "新疆", "朝鲜", "延吉", "韩国", "清真", "单县"]),
    ("西餐", ["萨莉亚"]),
    ("外卖", ["外卖"]),
    ("商圈", ["万象城", "环球港", "万达"]),
]

# 个别店名单点覆盖 / 补充（店名不好从关键词推断时）
TAG_OVERRIDES: dict[str, list[str]] = {
    "烫逍遥": ["火锅", "麻辣香锅"],
    "莫图小馆": ["家常小馆"],
    "醉胡桃小馆": ["家常小馆"],
    "那家餐厅": ["家常小馆"],
    "恒记饭店": ["家常小馆"],
    "陈记咱家厨房": ["家常小馆"],
    "小菜园": ["家常小馆"],
    "旺煮旺大排档": ["家常小馆"],
    "吃饭皇帝大": ["家常小馆"],
    "万象城吃饭皇帝大": ["家常小馆", "商圈"],
    "万达艾宴氏": ["商圈"],
    "麦禾常州菜": ["常州菜"],
}


def auto_tags(name: str) -> list[str]:
    """返回去重后的标签列表；无法识别时返回 ['其他']。"""
    tags: list[str] = []
    seen: set[str] = set()

    def add(tag: str) -> None:
        if tag not in seen:
            seen.add(tag)
            tags.append(tag)

    if name in TAG_OVERRIDES:
        for tag in TAG_OVERRIDES[name]:
            add(tag)

    for tag, keywords in TAG_RULES:
        if any(kw in name for kw in keywords):
            add(tag)

    if not tags:
        add("其他")
    return tags


def enrich_item(item: dict) -> dict:
    """为单条数据补全 tags 字段（保留已有手工标签并合并自动标签）。"""
    out = dict(item)
    auto = auto_tags(str(out.get("name") or ""))
    manual = out.get("tags")
    if isinstance(manual, list) and manual:
        merged: list[str] = []
        seen: set[str] = set()
        for tag in [*manual, *auto]:
            if isinstance(tag, str) and tag and tag not in seen:
                seen.add(tag)
                merged.append(tag)
        out["tags"] = merged
    else:
        out["tags"] = auto
    return out
