# Importing db from our Flask application.
from flask_sqlalchemy import SQLAlchemy


# Create the database object.
db = SQLAlchemy()


# Create the StudySession database model.
class StudySession(db.Model):

    # Unique ID for each study session.
    id = db.Column(db.Integer, primary_key=True)

    # Name/title of the study session.
    title = db.Column(db.String(100), nullable=False)

    # length of the study session in minutes
    duration = db.Column(db.Integer, nullable=False, default=30)

    # Current status of the study session.
    status = db.Column(db.String(20), nullable=False, default="not_started")

    # Remaining time in seconds
    remaining_time = db.Column(db.Integer, nullable=False, default=0)

    # connect this study session to all of its tasks
    tasks = db.relationship("Task", backref="study_session", lazy=True)

# Creating the Task database model.


class Task(db.Model):

    # Unique ID for each task.
    id = db.Column(db.Integer, primary_key=True)

    # Name/description of the task.
    title = db.Column(db.String(200), nullable=False)

    # Store how many minutes the task should take.
    duration = db.Column(db.Integer, nullable=False, default=30)

    # Stores whether the task has been completed.
    completed = db.Column(db.Boolean, default=False)

    # Stores the current status of the task.
    status = db.Column(db.String(20), nullable=False, default="upcoming")

    # Store the remaining time in seconds when the task is paused.
    remaining_time = db.Column(db.Integer, nullable=False, default=0)

    # Connect the task to its study session.
    study_session_id = db.Column(
        db.Integer, db.ForeignKey("study_session.id"), nullable=False
    )
# Create the Focus Interruption Record database model.


class FocusInterruptionRecord(db.Model):

    # Unique ID for each interruption record.
    id = db.Column(db.Integer, primary_key=True)

    # Store the ID of the task that was interrupted.
    task_id = db.Column(
        db.Integer, db.ForeignKey("task.id"), nullable=False
    )

    # Store when the interruption started.
    started_at = db.Column(db.DateTime, nullable=False)

    # Store when the user returned from the interruption.
    ended_at = db.Column(db.DateTime, nullable=True)

    # Connect the interruption record to its task.
    task = db.relationship("Task", backref="interruptions")
