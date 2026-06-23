from rules import ALL_RULES

CATEGORIES = ["color", "style", "pattern", "silhouette"]


def score_outfit(top_item, bottom_item):
    hits = []

    for rule_fn in ALL_RULES:
        try:
            hit = rule_fn(top_item, bottom_item)
            if hit:
                hits.append(hit)
        except Exception as e:
            print(f"規則 {rule_fn.__name__} 執行失敗: {e}")

    breakdown = {c: 0 for c in CATEGORIES}
    reasons = []
    warnings = []
    total = 0

    for hit in hits:
        category = hit.get("category", "other")
        delta = hit.get("delta", 0)
        kind = hit.get("kind", "reason")
        message = hit.get("message", "")

        breakdown[category] = breakdown.get(category, 0) + delta
        total += delta

        if kind == "warning":
            warnings.append(message)
        else:
            reasons.append(message)

    return {
        "items": {
            "top": top_item,
            "bottom": bottom_item
        },
        "score": total,
        "breakdown": breakdown,
        "reasons": reasons,
        "warnings": warnings,
        "hits": hits
    }


def rank_outfits(top_info_list, bottom_info_list, top_k=3):
    results = []

    for top_item in top_info_list:
        for bottom_item in bottom_info_list:
            result = score_outfit(top_item, bottom_item)
            results.append(result)

    results.sort(
        key=lambda x: (
            x["score"],
            len(x["reasons"]),
            -len(x["warnings"])
        ),
        reverse=True
    )

    return results[:top_k]