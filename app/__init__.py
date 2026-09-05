# Importing flask from the flask package, using flask to build the web application.
from flask import Flask, render_template, request
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

            # Create a new StudySession object.
            session = StudySession(title=title)

            # Add the new session to the database.
            db.session.add(session)

            # Save the changes to the database.
            db.session.commit()

            # Tell the user the session was created.
            return "Study session created!"

        # If the user has not submitted the form yet,
        # display the creation page.
        return render_template("create_session.html")

        # Route for viewing all study sessions.
    @app.route("/sessions")
    def view_sessions():

        # Route for creating a task.
        @app.route("/tasks/create/<int:session_id>", methods=["GET", "POST"])
        def create_task(session_id):

            # Find the study session this task belongs to.
            session = StudySession.query.get_or_404(session_id)

            # If the user submitted the form...
            if request.method == "POST":

                # Get the task title from the form.
                title = request.form["title"]

                # Create a new task and connect it to the study session.
                task = Task(title=title, study_session_id=session.id)

                # Add the task to the database.
                db.session.add(task)

                # Save the task.
                db.session.commit()

                # Confirm that the task was created.
                return "Task created!"

            # Display the task creation page.
            return render_template("create_task.html", session=session)

            # Get all study sessions from the database.
            sessions = StudySession.query.all()

            # Send the sessions to the HTML page.
            return render_template("sessions.html", sessions=sessions)

      # return application
    return app
