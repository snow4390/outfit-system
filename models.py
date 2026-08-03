import os
from typing import Any

from PIL import Image

from config import (
    VIT_MODEL_NAME,
    CLIP_MODEL_NAME,
    STYLE_LABELS,
    TOP_K_STYLE,
)
from color_analyzer import extract_color_features


# --------------------------------------------------
# 執行環境設定
# --------------------------------------------------

IS_VERCEL = bool(os.getenv("VERCEL"))

HF_TOKEN = os.getenv("HF_TOKEN", "")

vit_processor = None
vit_model = None
clip_processor = None
clip_model = None
torch = None
device = "cpu"


# --------------------------------------------------
# 本機環境：載入 Hugging Face 模型
# Vercel：不載入大型模型
# --------------------------------------------------

if not IS_VERCEL:
    try:
        import torch as torch_module

        from transformers import (
            AutoImageProcessor,
            AutoModelForImageClassification,
            CLIPProcessor,
            CLIPModel,
        )

        torch = torch_module
        device = "cuda" if torch.cuda.is_available() else "cpu"

        print("正在載入 ViT 衣物分類模型...")

        vit_processor = AutoImageProcessor.from_pretrained(
            VIT_MODEL_NAME
        )
        vit_model = AutoModelForImageClassification.from_pretrained(
            VIT_MODEL_NAME
        )
        vit_model.to(device)
        vit_model.eval()

        print("正在載入 CLIP 風格辨識模型...")

        clip_processor = CLIPProcessor.from_pretrained(
            CLIP_MODEL_NAME
        )
        clip_model = CLIPModel.from_pretrained(
            CLIP_MODEL_NAME
        )
        clip_model.to(device)
        clip_model.eval()

        print(f"Hugging Face 模型載入成功，目前裝置：{device}")

    except Exception as error:
        print(f"本機 Hugging Face 模型載入失敗：{error}")

        vit_processor = None
        vit_model = None
        clip_processor = None
        clip_model = None
        torch = None

else:
    print(
        "Vercel 環境：不載入 torch 與 transformers，"
        "改用 Hugging Face 雲端推論。"
    )


# --------------------------------------------------
# 預設結果
# --------------------------------------------------

def default_result() -> dict[str, Any]:
    return {
        "category": "未知",
        "style": "casual",
        "style_top3": [
            {
                "label": "casual",
                "score": 1.0,
            }
        ],
        "color": {},
        "pattern": {
            "label": "solid",
            "is_solid": True,
        },
        "fit": {
            "label": "regular",
        },
    }


# --------------------------------------------------
# 版型推測
# --------------------------------------------------

def infer_fit_by_category_and_style(
    category: str,
    style: str,
) -> dict[str, str]:
    category_text = str(category).lower()
    style_text = str(style).lower()

    if (
        "hoodie" in category_text
        or "sweatshirt" in category_text
    ):
        return {"label": "oversized"}

    if (
        "t-shirt" in category_text
        or "shirt" in category_text
        or "jersey" in category_text
        or "top" in category_text
    ):
        if style_text in ["street", "sport"]:
            return {"label": "oversized"}

        return {"label": "regular"}

    if (
        "jeans" in category_text
        or "trousers" in category_text
        or "pants" in category_text
    ):
        if style_text in ["street", "sport"]:
            return {"label": "regular"}

        return {"label": "slim"}

    if "skirt" in category_text:
        return {"label": "regular"}

    if "dress" in category_text:
        return {"label": "regular"}

    return {"label": "unknown"}


# --------------------------------------------------
# Hugging Face 雲端 Client
# --------------------------------------------------

def get_hf_client():
    if not HF_TOKEN:
        print("未設定 HF_TOKEN，無法使用 Hugging Face 雲端推論。")
        return None

    try:
        from huggingface_hub import InferenceClient

        return InferenceClient(
            token=HF_TOKEN,
            timeout=30,
        )

    except Exception as error:
        print(f"建立 Hugging Face Client 失敗：{error}")
        return None


# --------------------------------------------------
# 本機衣物分類
# --------------------------------------------------

def classify_category_local(image: Image.Image) -> str:
    if (
        vit_model is None
        or vit_processor is None
        or torch is None
    ):
        return "未知"

    inputs = vit_processor(
        images=image,
        return_tensors="pt",
    )
    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():
        outputs = vit_model(**inputs)

        predicted_index = outputs.logits.argmax(-1).item()

        category = vit_model.config.id2label.get(
            predicted_index,
            "未知",
        )

    return str(category).split(",")[0].strip()


# --------------------------------------------------
# Vercel 雲端衣物分類
# --------------------------------------------------

def classify_category_cloud(image_path: str) -> str:
    client = get_hf_client()

    if client is None:
        return "未知"

    try:
        results = client.image_classification(
            image=image_path,
            model=VIT_MODEL_NAME,
            top_k=1,
        )

        if not results:
            return "未知"

        first_result = results[0]

        if isinstance(first_result, dict):
            label = first_result.get("label", "未知")
        else:
            label = getattr(first_result, "label", "未知")

        return str(label).split(",")[0].strip()

    except Exception as error:
        print(f"Hugging Face 雲端衣物分類失敗：{error}")
        return "未知"


# --------------------------------------------------
# 本機風格分類
# --------------------------------------------------

def classify_style_local(
    image: Image.Image,
) -> tuple[str, list[dict[str, Any]]]:
    if (
        clip_model is None
        or clip_processor is None
        or torch is None
    ):
        return "casual", [
            {
                "label": "casual",
                "score": 1.0,
            }
        ]

    inputs = clip_processor(
        text=STYLE_LABELS,
        images=image,
        return_tensors="pt",
        padding=True,
    )
    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():
        outputs = clip_model(**inputs)

        logits = outputs.logits_per_image[0]
        probabilities = torch.softmax(logits, dim=0)

    top_k = min(TOP_K_STYLE, len(STYLE_LABELS))

    top_values, top_indexes = torch.topk(
        probabilities,
        k=top_k,
    )

    style_top3 = []

    for index, score in zip(
        top_indexes.tolist(),
        top_values.tolist(),
    ):
        style_top3.append(
            {
                "label": STYLE_LABELS[index],
                "score": round(float(score), 4),
            }
        )

    main_style = (
        style_top3[0]["label"]
        if style_top3
        else "casual"
    )

    return main_style, style_top3


# --------------------------------------------------
# Vercel 雲端風格分類
# --------------------------------------------------

def classify_style_cloud(
    image_path: str,
) -> tuple[str, list[dict[str, Any]]]:
    client = get_hf_client()

    if client is None:
        return "casual", [
            {
                "label": "casual",
                "score": 1.0,
            }
        ]

    try:
        results = client.zero_shot_image_classification(
            image=image_path,
            candidate_labels=STYLE_LABELS,
            model=CLIP_MODEL_NAME,
        )

        if not results:
            return "casual", [
                {
                    "label": "casual",
                    "score": 1.0,
                }
            ]

        parsed_results = []

        for result in results:
            if isinstance(result, dict):
                label = result.get("label", "unknown")
                score = result.get("score", 0)
            else:
                label = getattr(result, "label", "unknown")
                score = getattr(result, "score", 0)

            parsed_results.append(
                {
                    "label": str(label),
                    "score": round(float(score), 4),
                }
            )

        parsed_results.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        style_top3 = parsed_results[:TOP_K_STYLE]

        main_style = (
            style_top3[0]["label"]
            if style_top3
            else "casual"
        )

        return main_style, style_top3

    except Exception as error:
        print(f"Hugging Face 雲端風格分類失敗：{error}")

        return "casual", [
            {
                "label": "casual",
                "score": 1.0,
            }
        ]


# --------------------------------------------------
# 對外統一分類函式
# --------------------------------------------------

def classify_category(
    image: Image.Image | None = None,
    image_path: str | None = None,
) -> str:
    if IS_VERCEL:
        if not image_path:
            return "未知"

        return classify_category_cloud(image_path)

    if image is None:
        return "未知"

    return classify_category_local(image)


def classify_style(
    image: Image.Image | None = None,
    image_path: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    if IS_VERCEL:
        if not image_path:
            return "casual", [
                {
                    "label": "casual",
                    "score": 1.0,
                }
            ]

        return classify_style_cloud(image_path)

    if image is None:
        return "casual", [
            {
                "label": "casual",
                "score": 1.0,
            }
        ]

    return classify_style_local(image)


# --------------------------------------------------
# 完整圖片分析
# --------------------------------------------------

def classify_image(image_path: str) -> dict[str, Any]:
    result = default_result()

    try:
        result["color"] = extract_color_features(image_path)

    except Exception as error:
        print(f"顏色分析失敗：{error}")

    try:
        image = Image.open(image_path).convert("RGB")

        category = classify_category(
            image=image,
            image_path=image_path,
        )

        style, style_top3 = classify_style(
            image=image,
            image_path=image_path,
        )

        result["category"] = category
        result["style"] = style
        result["style_top3"] = style_top3

        result["fit"] = infer_fit_by_category_and_style(
            category,
            style,
        )

    except Exception as error:
        print(f"圖片分類失敗：{error}")

    return result
