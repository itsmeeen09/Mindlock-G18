# Importing flask from the flask package, using flask to build the web application.
from flask import Flask, render_template, request, redirect, url_for, jsonify
# bringing render tool from flask to display the html instead of text
# datetime
from datetime import datetime
# Import the database object.
from .models import db, StudySession, Task, FocusInterruptionRecord

# function for executes and creation flask application


def create_app():
    app = Flask(__name__)

    # Configure the database location.
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mindlock.db"

    # Turn off unnecessary modification tracking.
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Connect SQLAlchemy to our Flask application.
    db.init_app(app)

    # creating database tables from my models
    with app.app_context():
        db.create_all()

    # creating a route for the homepage
    @app.route("/")
    def home():

        # return this webpage
        return render_template("index.html")

    # Route for creating a new study session.
    @app.route("/sessions/create", methods=["GET", "POST"])
    def create_session():
        # If the user submitted the form...
        if request.method == "POST":

            # Get the session title from the form.
            title = request.form["title"]

        # Create a new StudySession object.
            session = StudySession(
                title=title
            )

        # Add the new session to the database.
            db.session.add(session)

        # Save the changes to the database.
            db.session.commit()

        # Send the user to the task creation page.
            return redirect(url_for("create_task", session_id=session.id))

    # If the user has not submitted the form yet,
    # display the creation page.
        return render_template("create_session.html")

    # Route for viewing all study sessions.

    @app.route("/sessions")
    def view_sessions():

        sessions = StudySession.query.all()

        return render_template("sessions.html", sessions=sessions)

    @app.route("/sessions/<int:session_id>/delete", methods=["POST"])
    def delete_session(session_id):

        # Find the study session.
        session = StudySession.query.get_or_404(session_id)

        # Delete all tasks belonging to this session.
        for task in session.tasks:
            db.session.delete(task)

        # Delete the study session.
        db.session.delete(session)

        # Save the changes.
        db.session.commit()

        # Return to the My Study Sessions page.
        return redirect(url_for("view_sessions"))
    # Route for creating a task.

    @app.route("/tasks/create/<int:session_id>", methods=["GET", "POST"])
    def create_task(session_id):

        # Find the study session that this task belongs to.
        session = StudySession.query.get_or_404(session_id)

    # Check if the user submitted the form.
        if request.method == "POST":

            # Get the task title from the form.
            title = request.form["title"]

        # Get the task duration from the form.
            duration = int(request.form["duration"])

        # Create a new task with the title and selected duration.
            task = Task(
                title=title,
                duration=duration,
                study_session_id=session.id
            )

        # Add the new task to the database.
            db.session.add(task)

        # Save the new task.
            db.session.commit()

        # Return to the My Study Sessions page.
            return redirect(url_for("view_sessions"))

    # Show the Create Task page.
        return render_template("create_task.html", session=session)
    # Route for Focus Mode.

    # Show the Focus Mode page for a specific task.

    @app.route("/tasks/<int:task_id>/focus")
    def task_focus_mode(task_id):

        # Find the task the user wants to focus on.
        task = Task.query.get_or_404(task_id)

    # Find all interruption records for this task.
        interruptions = FocusInterruptionRecord.query.filter_by(
            task_id=task.id
        ).all()

    # Calculate the total time spent away from Focus Mode.
        total_interruption_seconds = 0

        for interruption in interruptions:

            # Only count interruptions that have ended.
            if interruption.ended_at is not None:
                duration = interruption.ended_at - interruption.started_at
                total_interruption_seconds += int(duration.total_seconds())

    # Send the interruption information to the Focus Mode page.
        return render_template(
            "task_focus_mode.html",
            task=task,
            interruption_count=len(interruptions),
            interruption_time=total_interruption_seconds
        )

    # Route for starting an individual task.

    @app.route("/tasks/<int:task_id>/start", methods=["POST"])
    def start_task(task_id):

        # Find the task.
        task = Task.query.get_or_404(task_id)

    # If the task was already completed,
    # reset its timer to the original duration.
        if task.status == "completed":
            task.remaining_time = task.duration * 60

    # Change the task status to ongoing.
        task.status = "ongoing"

    # Make sure the task is not marked as completed.
        task.completed = False

    # Save the changes to the database.
        db.session.commit()

    # Send the user to Focus Mode for this specific task.
        return redirect(url_for("task_focus_mode", task_id=task.id))

    # Route for pausing an individual task.
    @app.route("/tasks/<int:task_id>/pause", methods=["POST"])
    def pause_task(task_id):

        # Find the task.
        task = Task.query.get_or_404(task_id)

        # Get the remaining time from the Focus Mode timer.
        remaining_time = request.form.get("remaining_time", type=int)

        # Keep the task as ongoing.
        task.status = "ongoing"

        # Save the remaining time.
        task.remaining_time = remaining_time

        # Save the changes to the database.
        db.session.commit()

        # Return to Task Focus Mode.
        return redirect(url_for("task_focus_mode", task_id=task.id))

    # Route for completing an individual task.
    @app.route("/tasks/<int:task_id>/complete", methods=["POST"])
    def complete_task(task_id):

        # Find the task.
        task = Task.query.get_or_404(task_id)

        # Mark the task as completed.
        task.status = "completed"

        # Keep the completed field in sync.
        task.completed = True

        # Set the remaining time to zero.
        task.remaining_time = 0

        # Save the changes to the database.
        db.session.commit()

        # Return to the My Tasks page.
        return redirect(url_for("view_tasks"))

    # Route for viewing all tasks.

    @app.route("/tasks")
    def view_tasks():

        sessions = StudySession.query.all()

        # Calculate completion percentage for each session.
        for session in sessions:

            total_tasks = len(session.tasks)

            completed_tasks = sum(
                1 for task in session.tasks
                if task.status == "completed"
            )

            if total_tasks > 0:
                session.progress = (completed_tasks / total_tasks) * 100
            else:
                session.progress = 0

        return render_template("tasks.html", sessions=sessions)

 # Route for changing a task's status

    @app.route("/tasks/<int:task_id>/status/<status>", methods=["POST"])
    def update_task_status(task_id, status):

        # Find the task.
        task = Task.query.get_or_404(task_id)

    # If the completed task is being redone,
    # reset its timer to the original duration.
        if status == "upcoming" and task.status == "completed":
            task.remaining_time = task.duration * 60

    # Update the task status.
        task.status = status

    # Keep the completed field in sync.
        task.completed = status == "completed"

    # Save the change to the database.
        db.session.commit()

    # Return to the My Tasks page.
        return redirect(url_for("view_tasks"))

    @app.route("/tasks/<int:task_id>/delete", methods=["POST"])
    def delete_task(task_id):

        # Find the task.
        task = Task.query.get_or_404(task_id)

        # Delete the task.
        db.session.delete(task)

        # Save the change.
        db.session.commit()

        # Return to the My Tasks page.
        return redirect(url_for("view_tasks"))


# Start a focus interruption record.


    @app.route("/tasks/<int:task_id>/interruptions/start", methods=["POST"])
    def start_interruption(task_id):

        # Find the task that was interrupted.
        task = Task.query.get_or_404(task_id)

    # Create a new interruption record.
        interruption = FocusInterruptionRecord(
            task_id=task.id,
            started_at=datetime.utcnow()
        )

    # Save the interruption record to the database.
        db.session.add(interruption)
        db.session.commit()

    # Send the interruption ID back to the browser.
        return jsonify({"interruption_id": interruption.id})


# End a focus interruption record.


    @app.route(
        "/tasks/<int:task_id>/interruptions/<int:record_id>/end",
        methods=["POST"]
    )
    def end_interruption(task_id, record_id):

        # Find the interruption record.
        interruption = FocusInterruptionRecord.query.get_or_404(record_id)

    # Record when the user returned.
        interruption.ended_at = datetime.utcnow()

    # Save the updated record.
        db.session.commit()

    # Confirm that the interruption was recorded.
        return jsonify({"success": True})

    # Get all focus interruption records for a task.

    @app.route("/tasks/<int:task_id>/interruptions", methods=["GET"])
    def get_interruptions(task_id):

        # Find all interruptions recorded for this task.
        interruptions = FocusInterruptionRecord.query.filter_by(
            task_id=task_id
        ).all()

    # Calculate the total interruption time.
        total_seconds = 0

        for interruption in interruptions:

            # Only calculate time for completed interruptions.
            if interruption.ended_at is not None:
                duration = interruption.ended_at - interruption.started_at
                total_seconds += int(duration.total_seconds())

    # Send the interruption information to the browser.
        return jsonify({
            "count": len(interruptions),
            "total_seconds": total_seconds
        })
# return application
    return app
