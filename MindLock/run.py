# Import the create_app function from my app package.
from app import create_app


# Creating the MindLock Flask application.
app = create_app()


# Start the Flask development server when this file is run directly.
if __name__ == "__main__":
    app.run(debug=True)
