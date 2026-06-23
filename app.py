from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
import os
import time
import uuid

from models import classify_image
from scorer import rank_outfits
from gemini_api import (
    generate_suggestion_gemini_from_ranked_outfits,
    generate_suggestion_text
)
from utils import allowed_file, clean_temp_files, ensure_dir, convert_webp_to_jpg
from config import UPLOAD_FOLDER, MAX_TOP_K
from database import db, login_manager
from auth import User, WardrobeItem

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "outfit_system_secret_key")

database_url = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:@localhost/outfit_system?charset=utf8mb4"
)

# Railway 的 MySQL 連線常常是 mysql:// 開頭
# SQLAlchemy 會預設找 MySQLdb，所以要改成 mysql+pymysql://
if database_url.startswith("mysql://"):
    database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db.init_app(app)
login_manager.init_app(app)

with app.app_context():
    db.create_all()

ensure_dir(app.config["UPLOAD_FOLDER"])


@app.route("/")
@login_required
def index():
    tops = WardrobeItem.query.filter_by(
        user_id=current_user.id,
        item_type="top"
    ).order_by(WardrobeItem.id.desc()).all()

    bottoms = WardrobeItem.query.filter_by(
        user_id=current_user.id,
        item_type="bottom"
    ).order_by(WardrobeItem.id.desc()).all()

    return render_template(
        "index.html",
        username=current_user.username,
        tops=tops,
        bottoms=bottoms
    )


@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "success": True,
        "message": "Outfit recommendation system is running."
    })


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not email or not password:
            flash("請完整填寫所有欄位。", "error")
            return render_template("register.html")

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash("使用者名稱或 Email 已存在。", "error")
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        user = User(
            username=username,
            email=email,
            password_hash=password_hash
        )
        db.session.add(user)
        db.session.commit()

        flash("註冊成功，請登入。", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("請輸入 Email 與密碼。", "error")
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("登入成功。", "success")
            return redirect(url_for("index"))

        flash("Email 或密碼錯誤。", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("你已成功登出。", "success")
    return redirect(url_for("login"))


@app.route("/closet")
@login_required
def closet():
    tops = WardrobeItem.query.filter_by(
        user_id=current_user.id,
        item_type="top"
    ).order_by(WardrobeItem.id.desc()).all()

    bottoms = WardrobeItem.query.filter_by(
        user_id=current_user.id,
        item_type="bottom"
    ).order_by(WardrobeItem.id.desc()).all()

    return render_template(
        "closet.html",
        tops=tops,
        bottoms=bottoms,
        username=current_user.username
    )


@app.route("/style-profile")
@login_required
def style_profile():
    items = WardrobeItem.query.filter_by(user_id=current_user.id).all()

    total = len(items)

    style_count = {}
    category_count = {}
    fit_count = {}

    for item in items:
        style = item.style or "未知"
        category = item.category or "未知"
        fit = item.fit_label or "未知"

        style_count[style] = style_count.get(style, 0) + 1
        category_count[category] = category_count.get(category, 0) + 1
        fit_count[fit] = fit_count.get(fit, 0) + 1

    def to_percent_dict(count_dict):
        if total == 0:
            return {}

        result = {}
        for key, value in count_dict.items():
            result[key] = round(value / total * 100, 1)
        return result

    style_percent = to_percent_dict(style_count)
    category_percent = to_percent_dict(category_count)
    fit_percent = to_percent_dict(fit_count)

    main_style = max(style_count, key=style_count.get) if style_count else "尚無資料"
    main_fit = max(fit_count, key=fit_count.get) if fit_count else "尚無資料"

    if total == 0:
        ai_summary = "目前衣櫃中還沒有衣物，請先上傳上衣或下裝，系統才能分析你的個人穿搭風格。"
    else:
        ai_summary = (
            f"你的衣櫃目前以「{main_style}」風格為主，"
            f"版型偏好則偏向「{main_fit}」。"
            f"整體來看，系統會根據這些衣物特徵，推薦更符合你日常穿搭習慣的組合。"
        )

    return render_template(
        "style_profile.html",
        username=current_user.username,
        total=total,
        style_percent=style_percent,
        category_percent=category_percent,
        fit_percent=fit_percent,
        main_style=main_style,
        main_fit=main_fit,
        ai_summary=ai_summary
    )


@app.route("/wardrobe-health")
@login_required
def wardrobe_health():
    items = WardrobeItem.query.filter_by(user_id=current_user.id).all()

    tops = [item for item in items if item.item_type == "top"]
    bottoms = [item for item in items if item.item_type == "bottom"]

    total = len(items)
    top_count = len(tops)
    bottom_count = len(bottoms)

    style_count = {}
    fit_count = {}
    category_count = {}

    for item in items:
        style = item.style or "未知"
        fit = item.fit_label or "未知"
        category = item.category or "未知"

        style_count[style] = style_count.get(style, 0) + 1
        fit_count[fit] = fit_count.get(fit, 0) + 1
        category_count[category] = category_count.get(category, 0) + 1

    main_style = max(style_count, key=style_count.get) if style_count else "尚無資料"
    main_fit = max(fit_count, key=fit_count.get) if fit_count else "尚無資料"

    suggestions = []

    if total == 0:
        suggestions.append("目前衣櫃中還沒有資料，建議先上傳至少 3 件上衣與 3 件下裝。")
    else:
        if top_count == 0:
            suggestions.append("目前缺少上衣資料，建議新增 T-shirt、襯衫或外套等單品。")
        elif bottom_count == 0:
            suggestions.append("目前缺少下裝資料，建議新增牛仔褲、長褲或裙裝等單品。")
        elif top_count >= bottom_count * 2:
            suggestions.append("上衣數量明顯多於下裝，建議補充更多褲子或裙裝，讓搭配選擇更平均。")
        elif bottom_count >= top_count * 2:
            suggestions.append("下裝數量明顯多於上衣，建議補充更多上衣，提升搭配變化。")
        else:
            suggestions.append("上衣與下裝比例大致平衡，衣櫃搭配基礎良好。")

        if len(style_count) <= 1:
            suggestions.append("目前風格較集中，建議增加不同風格的單品，例如休閒、正式、街頭或簡約風。")
        else:
            suggestions.append(f"你的衣櫃主要偏向「{main_style}」風格，可依照這個方向建立更一致的個人穿搭。")

        if main_fit == "unknown" or main_fit == "未知":
            suggestions.append("目前版型資料不足，建議之後強化影像辨識中的版型分析。")
        else:
            suggestions.append(f"你的衣櫃常見版型為「{main_fit}」，可以再補充不同版型來增加穿搭層次。")

        if total < 6:
            suggestions.append("目前衣物數量偏少，建議至少累積 6 件以上，系統推薦會更準確。")

    health_score = 0

    if total >= 6:
        health_score += 30
    elif total >= 3:
        health_score += 20
    elif total > 0:
        health_score += 10

    if top_count > 0 and bottom_count > 0:
        health_score += 30

    if top_count > 0 and bottom_count > 0:
        ratio = min(top_count, bottom_count) / max(top_count, bottom_count)
        if ratio >= 0.5:
            health_score += 20
        else:
            health_score += 10

    if len(style_count) >= 2:
        health_score += 20
    elif len(style_count) == 1:
        health_score += 10

    if health_score >= 85:
        health_level = "衣櫃狀態良好"
    elif health_score >= 70:
        health_level = "衣櫃基礎完整"
    elif health_score >= 50:
        health_level = "衣櫃仍可補強"
    else:
        health_level = "衣櫃資料不足"

    return render_template(
        "wardrobe_health.html",
        username=current_user.username,
        total=total,
        top_count=top_count,
        bottom_count=bottom_count,
        main_style=main_style,
        main_fit=main_fit,
        category_count=category_count,
        style_count=style_count,
        fit_count=fit_count,
        suggestions=suggestions,
        health_score=health_score,
        health_level=health_level
    )


@app.route("/closet/upload", methods=["POST"])
@login_required
def closet_upload():
    top_files = request.files.getlist("tops")
    bottom_files = request.files.getlist("bottoms")

    user_folder = os.path.join(app.config["UPLOAD_FOLDER"], f"user_{current_user.id}")
    ensure_dir(user_folder)

    uploaded = 0
    has_top = any(file and file.filename for file in top_files)
    has_bottom = any(file and file.filename for file in bottom_files)

    if not has_top and not has_bottom:
        flash("請至少選擇一張上衣或下裝圖片。", "error")
        return redirect(url_for("closet"))

    def process_files(files, item_type):
        nonlocal uploaded

        for file in files:
            if not file or file.filename == "":
                continue

            if not allowed_file(file.filename):
                continue

            filename = secure_filename(f"{item_type}_{uuid.uuid4().hex}_{file.filename}")
            path = os.path.join(user_folder, filename)
            file.save(path)

            final_path = convert_webp_to_jpg(path)

            try:
                info = classify_image(final_path)
            except Exception as e:
                print(f"分類失敗: {file.filename}, error={e}")
                continue

            item = WardrobeItem(
                user_id=current_user.id,
                item_type=item_type,
                image_path=final_path.replace("\\", "/"),
                original_filename=file.filename,
                category=info.get("category"),
            style=info.get("style"),
            fit_label=(info.get("fit") or {}).get("label"),
            style_top3=info.get("style_top3"),
            color=info.get("color"),
            pattern=info.get("pattern")
            )

            db.session.add(item)
            uploaded += 1

    process_files(top_files, "top")
    process_files(bottom_files, "bottom")

    db.session.commit()

    if uploaded == 0:
        flash("沒有成功上傳任何衣物，請確認圖片格式是否正確。", "error")
    else:
        flash(f"成功上傳 {uploaded} 件衣物", "success")

    return redirect(url_for("closet"))


@app.route("/closet/delete/<int:item_id>", methods=["POST"])
@login_required
def closet_delete(item_id):
    item = WardrobeItem.query.filter_by(id=item_id, user_id=current_user.id).first()

    if not item:
        flash("找不到這件衣服。", "error")
        return redirect(url_for("closet"))

    try:
        if item.image_path and os.path.exists(item.image_path):
            os.remove(item.image_path)
    except Exception as e:
        print(f"刪除衣櫃圖片失敗: {e}")

    db.session.delete(item)
    db.session.commit()

    flash("已從衣櫃刪除。", "success")
    return redirect(url_for("closet"))


@app.route("/analyze", methods=["POST"])
@login_required
def analyze_outfit():
    text_query = request.form.get("text_query", "").strip()
    top_item_ids = [int(x) for x in request.form.getlist("top_item_ids") if x.isdigit()]
    bottom_item_ids = [int(x) for x in request.form.getlist("bottom_item_ids") if x.isdigit()]

    try:
        all_tops = WardrobeItem.query.filter_by(
            user_id=current_user.id,
            item_type="top"
        ).order_by(WardrobeItem.id.desc()).all()

        all_bottoms = WardrobeItem.query.filter_by(
            user_id=current_user.id,
            item_type="bottom"
        ).order_by(WardrobeItem.id.desc()).all()

        if not all_tops or not all_bottoms:
            return jsonify({
                "success": False,
                "error": "衣櫃中的上衣或下裝不足，無法產生搭配。"
            }), 400

        if not top_item_ids and not bottom_item_ids and not text_query:
            return jsonify({
                "success": False,
                "error": "請至少勾選衣物，或輸入補充需求。"
            }), 400

        selected_tops = WardrobeItem.query.filter(
            WardrobeItem.user_id == current_user.id,
            WardrobeItem.item_type == "top",
            WardrobeItem.id.in_(top_item_ids)
        ).all() if top_item_ids else []

        selected_bottoms = WardrobeItem.query.filter(
            WardrobeItem.user_id == current_user.id,
            WardrobeItem.item_type == "bottom",
            WardrobeItem.id.in_(bottom_item_ids)
        ).all() if bottom_item_ids else []

        if top_item_ids and not selected_tops:
            return jsonify({
                "success": False,
                "error": "找不到所選的上衣，請重新整理後再試。"
            }), 400

        if bottom_item_ids and not selected_bottoms:
            return jsonify({
                "success": False,
                "error": "找不到所選的下裝，請重新整理後再試。"
            }), 400

        top_candidates = selected_tops if selected_tops else all_tops
        bottom_candidates = selected_bottoms if selected_bottoms else all_bottoms

        def to_info(item, item_type):
            return {
                "wardrobe_id": item.id,
                "category": item.category or "未知",
                "style": item.style or "未知",
                "style_top3": item.style_top3 or [],
                "color": item.color or {},
                "pattern": item.pattern or {
                    "label": "solid",
                    "is_solid": True
                },
                "fit": {
                    "label": item.fit_label or "unknown"
                },
                "item_type": item_type,
                "source_index": 0,
                "image_path": item.image_path,
                "original_filename": item.original_filename
    }

        top_info_list = [to_info(item, "top") for item in top_candidates]
        bottom_info_list = [to_info(item, "bottom") for item in bottom_candidates]

        ranked_outfits = rank_outfits(
            top_info_list=top_info_list,
            bottom_info_list=bottom_info_list,
            top_k=MAX_TOP_K
        )

        if not ranked_outfits:
            return jsonify({
                "success": False,
                "error": "目前無法產生搭配結果，請換一批衣物或補充更多需求再試一次。"
            }), 500

        suggestion = generate_suggestion_gemini_from_ranked_outfits(
            ranked_outfits=ranked_outfits,
            user_text=text_query if text_query else None
        )

        used_top_ids = []
        used_bottom_ids = []

        for outfit in ranked_outfits:
            top_item = outfit.get("items", {}).get("top", {})
            bottom_item = outfit.get("items", {}).get("bottom", {})

            top_id = top_item.get("wardrobe_id")
            bottom_id = bottom_item.get("wardrobe_id")

            if top_id is not None and top_id not in used_top_ids:
                used_top_ids.append(top_id)

            if bottom_id is not None and bottom_id not in used_bottom_ids:
                used_bottom_ids.append(bottom_id)

        used_top_info = [
            item for item in top_info_list
            if item.get("wardrobe_id") in used_top_ids
        ]
        used_bottom_info = [
            item for item in bottom_info_list
            if item.get("wardrobe_id") in used_bottom_ids
        ]

        return jsonify({
            "success": True,
            "mode": "smart_selection",
            "analysis": {
                "top": used_top_info,
                "bottom": used_bottom_info
            },
            "ranked_outfits": ranked_outfits,
            "recommendation": suggestion
        })

    except Exception as e:
        print(f"分析失敗: {e}")
        return jsonify({
            "success": False,
            "error": "分析失敗，請稍後再試。"
        }), 500


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug_mode)
