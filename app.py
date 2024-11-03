from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import openai
import os
from sqlalchemy import text
from rapidfuzz import fuzz, process
import json
import logging
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables and set up logging
load_dotenv()
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

# Debug environment variables
logging.debug("Loading environment variables")
openai_api_key = os.getenv("OPENAI_API_KEY", "")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")
db_port = os.getenv('DB_PORT', '3306')

# Check if key environment variables are loaded
logging.debug(f"OPENAI_API_KEY: {openai_api_key}")
logging.debug(f"DB_USER: {db_user}")
logging.debug(f"DB_PASSWORD: {'Yes' if db_password else 'No'}")
logging.debug(f"DB_HOST: {db_host}")
logging.debug(f"DB_PORT: {db_port}")
logging.debug(f"DB_NAME: {db_name}")

try:
    db_port = int(db_port)
except ValueError:
    db_port = 3306  # Default fallback for MySQL

# Initialize OpenAI API key
openai.api_key = openai_api_key
if not openai.api_key:
    logging.error("OpenAI API key is missing!")

# Configure database URI
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Test database connection
try:
    logging.debug("Attempting to connect to the database...")
    with app.app_context():
        db.session.execute("SELECT 1")
    logging.info("Database connection successful.")
except Exception as e:
    logging.error(f"Database connection failed: {str(e)}")

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255), nullable=False)
    photo1 = db.Column(db.String(255))
    photo2 = db.Column(db.String(255))
    photo3 = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'photo1': self.get_photo_url(self.photo1),
            'photo2': self.get_photo_url(self.photo2),
            'photo3': self.get_photo_url(self.photo3)
        }

    @staticmethod
    def get_photo_url(photo):
        if photo and photo.startswith('photo/'):
            return f'https://haluansama.com/crm-sales/{photo}'
        return 'https://via.placeholder.com/150'


def detect_user_intent(user_message):
    try:
        logging.debug(f"Detecting intent for user message: {user_message}")
        gpt_intent_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
                        You are an assistant for Hardware Store. You name is F.Y.H Smart Agent that detects the user's intent...
                    """
                },
                {"role": "user", "content": f"{user_message}"}
            ],
            max_tokens=100,
            temperature=0.3,
        )
        intent_response = gpt_intent_response['choices'][0]['message']['content'].strip()
        logging.debug(f"OpenAI intent response: {intent_response}")
        return json.loads(intent_response)
    except Exception as e:
        logging.error(f"Error in detect_user_intent: {str(e)}")
        return {"intent": "general", "response": "Hello! How may I assist you today?"}


@app.route('/chat', methods=['POST'])
def handle_chat():
    try:
        user_message = request.json.get('message')
        selected_category = request.json.get('category')
        loggedInUsername = request.json.get('username')
        
        logging.debug(f"User message: {user_message}")
        logging.debug(f"Selected category: {selected_category}")
        logging.debug(f"Logged-in username: {loggedInUsername}")
        
        intent_data = detect_user_intent(user_message)
        intent = intent_data.get("intent")
        response = intent_data.get("response")
        
        logging.debug(f"Detected intent: {intent}")
        logging.debug(f"Response from OpenAI intent detection: {response}")
        
        if intent == "general":
            return jsonify({"response": response})
        elif intent == "sales_order":
            if selected_category == "sales_order":
                return sales_order_inquiry(loggedInUsername)
            else:
                return jsonify({"response": "Please switch to the 'Sales Order' category to proceed."})
        elif intent == "product_search":
            if selected_category == "search_product":
                search_term = user_message
                return search_products(search_term=search_term)
            else:
                return jsonify({"response": "Please switch to the 'Product Search' category to proceed."})
        else:
            return jsonify({"response": "Sorry, I didn't understand that. Can you clarify?"})

    except Exception as e:
        logging.error(f"Error in handle_chat: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/')
def index():
    return "Welcome to the GPT-4 Flask API! Use /chat to interact with the AI."

if __name__ == '__main__':
    # For Railway deployment, use host 0.0.0.0 and the PORT environment variable
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
