from PIL import Image
import os

from config import VIT_MODEL_NAME, CLIP_MODEL_NAME, STYLE_LABELS, TOP_K_STYLE
from color_analyzer import extract_color_features

IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID")

vit_processor = None
vit_model = None
clip_processor = None
clip_model = None
device = "cpu"

if not IS_RAILWAY:
    try:
        import torch
        from transformers import (
            AutoImageProcessor,
            AutoModelForImageClassification,
            CLIPProcessor,
            CLIPModel,
        )

        device = "cuda" if torch.cuda.is_available() else "cpu"

        vit_processor = AutoImageProcessor.from_pretrained(VIT_MODEL_NAME)
        vit_model = AutoModelForImageClassification.from_pretrained(VIT_MODEL_NAME)
        vit_model.to(device)
        vit_model.eval()

        clip_processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
        clip_model = CLIPModel.from_pretrained(CLIP_MODEL_NAME)
        clip_model.to(device)
        clip_model.eval()

        print(f"Hugging Face 模型載入成功！目前裝置：{device}")

    except Exception as e:
        print(f"Hugging Face 模型載入失敗: {e}")
else:
    print("Railway 環境：已自動啟用輕量展示模式，不載入 Hugging Face 模型。")


def default_result():
    return {
        "category": "未知",
        "style": "休閒風",
        "style_top3": [
            {
                "label": "休閒風",
                "score": 1.0
            }
        ],
        "color": {},
        "pattern": {
            "label": "solid",
            "is_solid": True
        },
        "fit": {
            "label": "regular"
        }
    }


def infer_fit_by_category_and_style(category, style):
    category = str(category).lower()
    style = str(style).lower()

    if "hoodie" in category or "sweatshirt" in category:
        return {"label": "oversized"}

    if "t-shirt" in category or "shirt" in category:
        return {"label": "regular"}

    if "jeans" in category or "trousers" in category or "pants" in category:
        if style in ["streetwear", "sporty"]:
            return {"label": "regular"}
        return {"label": "slim"}

    if "skirt" in category:
        return {"label": "regular"}

    return {"label": "unknown"}


def classify_category(image):
    if not vit_model or not vit_processor:
        return "未知"

    vit_inputs = vit_processor(images=image, return_tensors="pt")
    vit_inputs = {k: v.to(device) for k, v in vit_inputs.items()}

    with torch.no_grad():
        vit_outputs = vit_model(**vit_inputs)
        vit_idx = vit_outputs.logits.argmax(-1).item()
        category = vit_model.config.id2label.get(vit_idx, "未知")

    return str(category).split(",")[0].strip()


def classify_style(image):
    if not clip_model or not clip_processor:
        return "休閒風", [{"label": "休閒風", "score": 1.0}]

    clip_inputs = clip_processor(
        text=STYLE_LABELS,
        images=image,
        return_tensors="pt",
        padding=True
    )
    clip_inputs = {k: v.to(device) for k, v in clip_inputs.items()}

    with torch.no_grad():
        clip_outputs = clip_model(**clip_inputs)
        logits = clip_outputs.logits_per_image[0]
        probs = torch.softmax(logits, dim=0)

    topk = min(TOP_K_STYLE, len(STYLE_LABELS))
    top_vals, top_idxs = torch.topk(probs, k=topk)

    style_top3 = []
    for idx, score in zip(top_idxs.tolist(), top_vals.tolist()):
        style_top3.append({
            "label": STYLE_LABELS[idx],
            "score": round(float(score), 4)
        })

    main_style = style_top3[0]["label"] if style_top3 else "休閒風"
    return main_style, style_top3


def classify_image(image_path):
    result = default_result()

    try:
        result["color"] = extract_color_features(image_path)
    except Exception as e:
        print(f"顏色分析失敗: {e}")

    if IS_RAILWAY:
        return result

    try:
        image = Image.open(image_path).convert("RGB")

        category = classify_category(image)
        style, style_top3 = classify_style(image)

        result["category"] = category
        result["style"] = style
        result["style_top3"] = style_top3
        result["fit"] = infer_fit_by_category_and_style(category, style)

    except Exception as e:
        print(f"分類失敗: {e}")

    return result
