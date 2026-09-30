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
# Study session model
class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)

    # Session duration is kept for compatibility with the study system.
    duration = db.Column(db.Integer, nullable=False, default=30)

    # Stores the current session status.
    status = db.Column(db.String(20), nullable=False, default="not_started")

    # Stores remaining time when a task is paused.
    remaining_time = db.Column(db.Integer, nullable=False, default=0)

    # A study session can contain multiple tasks.
    tasks = db.relationship("Task", backref="study_session", lazy=True)


# Task model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)

    # Each task has its own duration.
    duration = db.Column(db.Integer, nullable=False, default=30)

    # True when the task has been completed.
    completed = db.Column(db.Boolean, default=False)

    # Stores the task's current status.
    status = db.Column(db.String(20), nullable=False, default="upcoming")

    # Stores remaining time when the task is paused.
    remaining_time = db.Column(db.Integer, nullable=False, default=0)

    # Links the task to its study session.
    study_session_id = db.Column(
        db.Integer,
        db.ForeignKey("study_session.id"),
        nullable=False
    )


# Focus interruption record model
class FocusInterruptionRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Links the interruption to the task being worked on.
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("task.id"),
        nullable=False
    )

    # Time when the user left Focus Mode.
    started_at = db.Column(db.DateTime, nullable=False)

    # Time when the user returned to Focus Mode.
    ended_at = db.Column(db.DateTime, nullable=True)

    # Allows interruptions to be accessed from a task.
    task = db.relationship("Task", backref="interruptions")