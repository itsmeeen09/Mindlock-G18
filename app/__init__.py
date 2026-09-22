# Importing flask from the flask package, using flask to build the web application.
from flask import Flask, render_template, request, redirect, url_for
# bringing render tool from flask to display the html instead of text

# Import the database object.
from .models import db, StudySession, Task

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

            # get the duration from the form
            duration = request.form["duration"]

            # Create a new StudySession object.
            session = StudySession(
                title=title,
                duration=int(duration)
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

    # Route for Focus Mode for an individual task.
    @app.route("/tasks/<int:task_id>/focus")
    def task_focus_mode(task_id):

        # Find the task.
        task = Task.query.get_or_404(task_id)

        # Display the Task Focus Mode page.
        return render_template("task_focus_mode.html", task=task)

    @app.route("/sessions/<int:session_id>/focus")
    def focus_mode(session_id):

        # Find the study session.
        session = StudySession.query.get_or_404(session_id)

        # Display the Focus Mode page.
        return render_template("focus_mode.html", session=session)

    # Route for starting an individual task.
    @app.route("/tasks/<int:task_id>/start", methods=["POST"])
    def start_task(task_id):

        # Find the task.
        task = Task.query.get_or_404(task_id)

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

# Route for starting a study session.

    @app.route("/sessions/<int:session_id>/start", methods=["POST"])
    def start_session(session_id):

        # Find the study session.
        session = StudySession.query.get_or_404(session_id)

        # Change the session status to active.
        session.status = "active"

        # Save the change to the database.
        db.session.commit()

        # Return to Focus Mode.
        return redirect(url_for("focus_mode", session_id=session.id))

    # Route for pausing a study session.
    @app.route("/sessions/<int:session_id>/pause", methods=["POST"])
    def pause_session(session_id):
        session = StudySession.query.get_or_404(session_id)

        remaining_time = request.form.get("remaining_time", type=int)

        session.status = "paused"
        session.remaining_time = remaining_time

        db.session.commit()
        return redirect(url_for("focus_mode", session_id=session.id))

    # Route for ending a study session.
    @app.route("/sessions/<int:session_id>/end", methods=["POST"])
    def end_session(session_id):
        session = StudySession.query.get_or_404(session_id)

        session.status = "completed"
        session.remaining_time = 0

        db.session.commit()

        return redirect(url_for("view_sessions"))
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

 # Route for changing a task's status.

    @app.route("/tasks/<int:task_id>/status/<status>", methods=["POST"])
    def update_task_status(task_id, status):

        # Find the task.
        task = Task.query.get_or_404(task_id)

        # Update the task status.
        task.status = status

        # Keep the completed field in sync.
        task.completed = status == "completed"

        # Save the change.
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

# return application
    return app
