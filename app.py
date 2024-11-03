from flask import Flask
import os
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Log that the app has started
logging.debug("App has started. Loading environment variables...")

# Load and log environment variables for debugging (mask sensitive info)
openai_api_key = os.getenv("OPENAI_API_KEY", "Not Set")
db_user = os.getenv("DB_USER", "Not Set")
db_password = os.getenv("DB_PASSWORD", "Not Set")
db_host = os.getenv("DB_HOST", "Not Set")
db_name = os.getenv("DB_NAME", "Not Set")
db_port = os.getenv("DB_PORT", "3306")

logging.debug(f"OPENAI_API_KEY: {'Set' if openai_api_key != 'Not Set' else 'Not Set'}")
logging.debug(f"DB_USER: {db_user}")
logging.debug(f"DB_PASSWORD: {'Set' if db_password != 'Not Set' else 'Not Set'}")
logging.debug(f"DB_HOST: {db_host}")
logging.debug(f"DB_NAME: {db_name}")
logging.debug(f"DB_PORT: {db_port}")

# Ensure DB_PORT is an integer
try:
    db_port = int(db_port)
except ValueError:
    db_port = 3306  # Default to 3306 if not a valid integer
    logging.warning("Invalid DB_PORT value. Defaulting to 3306.")

# Configure the SQLAlchemy database URI
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Test database connection
try:
    logging.debug("Attempting to connect to the database...")
    with app.app_context():
        db.session.execute(text("SELECT 1"))
    logging.info("Database connection successful.")
except Exception as e:
    logging.error(f"Database connection failed: {str(e)}")

# Define a simple route for testing
@app.route('/')
def index():
    return "Debugging Flask App: Check your logs for detailed information."

if __name__ == '__main__':
    # For Railway deployment, use host 0.0.0.0 and the PORT environment variable
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
