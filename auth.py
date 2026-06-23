from flask_login import UserMixin
from database import db, login_manager


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class WardrobeItem(db.Model):
    __tablename__ = "wardrobe_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    item_type = db.Column(db.String(20), nullable=False)   # top / bottom
    image_path = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=True)


    category = db.Column(db.String(100), nullable=True)
    style = db.Column(db.String(100), nullable=True)
    fit_label = db.Column(db.String(50), nullable=True)

    style_top3 = db.Column(db.JSON, nullable=True)
    color = db.Column(db.JSON, nullable=True)
    pattern = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))