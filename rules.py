def hue_diff(h1, h2):
    d = abs(h1 - h2) % 360
    return min(d, 360 - d)


def get_style_labels(item):
    return {x["label"] for x in item.get("style_top3", [])}


def has_style(item, target):
    return target in get_style_labels(item)


def get_fit(item):
    return item.get("fit", {}).get("label", "unknown")


# -------------------------
# Color rules
# -------------------------
def rule_C1_same_hue(top, bottom):
    h1 = top["color"]["main_hsv"][0]
    h2 = bottom["color"]["main_hsv"][0]
    if hue_diff(h1, h2) <= 15:
        return {
            "rule_id": "C1",
            "category": "color",
            "delta": 20,
            "message": "同色系搭配，整體更協調",
            "kind": "reason"
        }
    return None


def rule_C2_analogous_hue(top, bottom):
    h1 = top["color"]["main_hsv"][0]
    h2 = bottom["color"]["main_hsv"][0]
    d = hue_diff(h1, h2)
    if 15 < d <= 45:
        return {
            "rule_id": "C2",
            "category": "color",
            "delta": 12,
            "message": "類似色搭配，有層次但不突兀",
            "kind": "reason"
        }
    return None


def rule_C3_neutral_safe(top, bottom):
    if top["color"]["is_neutral"] or bottom["color"]["is_neutral"]:
        return {
            "rule_id": "C3",
            "category": "color",
            "delta": 10,
            "message": "中性色很好配，整體更穩定",
            "kind": "reason"
        }
    return None


def rule_C4_both_high_saturation(top, bottom):
    s1 = top["color"]["main_hsv"][1]
    s2 = bottom["color"]["main_hsv"][1]
    if s1 >= 0.65 and s2 >= 0.65:
        return {
            "rule_id": "C4",
            "category": "color",
            "delta": -15,
            "message": "兩件都高彩度容易太花，建議留一件低彩度或中性色",
            "kind": "warning"
        }
    return None


def rule_C5_brightness_contrast(top, bottom):
    v1 = top["color"]["main_hsv"][2]
    v2 = bottom["color"]["main_hsv"][2]
    if abs(v1 - v2) >= 0.35:
        return {
            "rule_id": "C5",
            "category": "color",
            "delta": 8,
            "message": "明度有對比，看起來更俐落",
            "kind": "reason"
        }
    return None


def rule_C6_both_dark_and_close(top, bottom):
    v1 = top["color"]["main_hsv"][2]
    v2 = bottom["color"]["main_hsv"][2]
    if abs(v1 - v2) < 0.15 and v1 < 0.35 and v2 < 0.35:
        return {
            "rule_id": "C6",
            "category": "color",
            "delta": -8,
            "message": "上下都暗且接近，容易顯得厚重；可加亮色鞋包提亮",
            "kind": "warning"
        }
    return None


def rule_C7_complementary_like(top, bottom):
    h1 = top["color"]["main_hsv"][0]
    h2 = bottom["color"]["main_hsv"][0]
    d = hue_diff(h1, h2)
    if 150 <= d <= 210:
        return {
            "rule_id": "C7",
            "category": "color",
            "delta": 10,
            "message": "上下色相有互補感，搭配有視覺亮點",
            "kind": "reason"
        }
    return None


# -------------------------
# Style rules
# -------------------------
def rule_S1_overlap_ge2(top, bottom):
    overlap = len(get_style_labels(top) & get_style_labels(bottom))
    if overlap >= 2:
        return {
            "rule_id": "S1",
            "category": "style",
            "delta": 20,
            "message": "上下風格一致，整體完成度高",
            "kind": "reason"
        }
    return None


def rule_S2_overlap_eq1(top, bottom):
    overlap = len(get_style_labels(top) & get_style_labels(bottom))
    if overlap == 1:
        return {
            "rule_id": "S2",
            "category": "style",
            "delta": 10,
            "message": "風格大致一致，搭配自然",
            "kind": "reason"
        }
    return None


def rule_S3_formal_vs_sporty_conflict(top, bottom):
    formal = has_style(top, "formal") or has_style(bottom, "formal")
    sporty = has_style(top, "sporty") or has_style(bottom, "sporty")
    if formal and sporty:
        return {
            "rule_id": "S3",
            "category": "style",
            "delta": -20,
            "message": "正式與運動元素衝突較大，可用中性色或簡約款過渡",
            "kind": "warning"
        }
    return None


def rule_S4_minimal_elegant_bonus(top, bottom):
    cond1 = has_style(top, "minimal") and has_style(bottom, "elegant")
    cond2 = has_style(top, "elegant") and has_style(bottom, "minimal")
    if cond1 or cond2:
        return {
            "rule_id": "S4",
            "category": "style",
            "delta": 8,
            "message": "簡約與優雅風格能互相加分，整體感更成熟",
            "kind": "reason"
        }
    return None


# -------------------------
# Pattern rules
# -------------------------
def rule_P1_both_not_solid(top, bottom):
    if (not top["pattern"]["is_solid"]) and (not bottom["pattern"]["is_solid"]):
        return {
            "rule_id": "P1",
            "category": "pattern",
            "delta": -15,
            "message": "上下都有圖案容易視覺太滿，建議其中一件換素色",
            "kind": "warning"
        }
    return None


def rule_P2_has_solid(top, bottom):
    if top["pattern"]["is_solid"] or bottom["pattern"]["is_solid"]:
        return {
            "rule_id": "P2",
            "category": "pattern",
            "delta": 6,
            "message": "有素色做留白，視覺更乾淨",
            "kind": "reason"
        }
    return None


# -------------------------
# Silhouette rules
# -------------------------
def rule_F1_oversized_top_slim_bottom(top, bottom):
    top_fit = get_fit(top)
    bottom_fit = get_fit(bottom)
    if top_fit == "oversized" and bottom_fit == "slim":
        return {
            "rule_id": "F1",
            "category": "silhouette",
            "delta": 12,
            "message": "上寬下窄的比例通常更修飾身形",
            "kind": "reason"
        }
    return None


def rule_F2_both_oversized(top, bottom):
    top_fit = get_fit(top)
    bottom_fit = get_fit(bottom)
    if top_fit == "oversized" and bottom_fit == "oversized":
        return {
            "rule_id": "F2",
            "category": "silhouette",
            "delta": -10,
            "message": "上下都偏寬鬆可能讓整體輪廓較膨脹",
            "kind": "warning"
        }
    return None


def rule_F3_both_unknown(top, bottom):
    top_fit = get_fit(top)
    bottom_fit = get_fit(bottom)
    if top_fit == "unknown" and bottom_fit == "unknown":
        return {
            "rule_id": "F3",
            "category": "silhouette",
            "delta": 0,
            "message": "目前版型資訊不足，暫不加減分",
            "kind": "reason"
        }
    return None


ALL_RULES = [
    rule_C1_same_hue,
    rule_C2_analogous_hue,
    rule_C3_neutral_safe,
    rule_C4_both_high_saturation,
    rule_C5_brightness_contrast,
    rule_C6_both_dark_and_close,
    rule_C7_complementary_like,
    rule_S1_overlap_ge2,
    rule_S2_overlap_eq1,
    rule_S3_formal_vs_sporty_conflict,
    rule_S4_minimal_elegant_bonus,
    rule_P1_both_not_solid,
    rule_P2_has_solid,
    rule_F1_oversized_top_slim_bottom,
    rule_F2_both_oversized,
    rule_F3_both_unknown,
]