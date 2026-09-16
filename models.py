from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin


db = SQLAlchemy()

from datetime import datetime, date

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    icon = db.Column(db.String(50), default="🏆")  # Emoji or icon class
    coin_reward = db.Column(db.Integer, default=0)

class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)

    achievement = db.relationship('Achievement')

class Streak(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    current_streak = db.Column(db.Integer, default=0)
    best_streak = db.Column(db.Integer, default=0)
    last_study_date = db.Column(db.Date, nullable=True)

    user = db.relationship('User', backref=db.backref('streak_info', uselist=False))
    
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    coins = db.Column(db.Integer, default=100)
    has_2hr_pass = db.Column(db.Boolean, default=False)
    theme = db.Column(db.String(20), default='pink')  # 'pink', 'matcha', 'lavender', etc.
    has_custom_themes = db.Column(db.Boolean, default=False)
    unlocked_themes = db.Column(db.String(200), default='pastel')
    achievements = db.relationship('UserAchievement', backref='user', lazy=True)

class FocusCoin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StudyPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pass_type = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)