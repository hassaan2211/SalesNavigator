from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import openai
import os
from dotenv import load_dotenv
from sqlalchemy import text
from rapidfuzz import fuzz, process
import json
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY", "")

load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{os.getenv('CPANEL_DB_USER')}:{os.getenv('CPANEL_DB_PASSWORD')}"
    f"@{os.getenv('CPANEL_DB_HOST')}/{os.getenv('CPANEL_DB_NAME')}"
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


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
        gpt_intent_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
                        You are an assistant for Hardware Store, You name is F.Y.H Smart Agent that detects the user's intent and responds accordingly. Possible intents include:
                        - general: for greetings, or If questions regarding general are asked reply using QUESTIONS and answers.  QUESTIONS and answers are only for general
                        - sales_order: when the user is asking about an order or sales order inquiry like "Search for sales order", "Search for order", "which is the most sold product". 
                        - product_search: when the user is asking to search like "Search for product drills", "Looking for drills", if someone mention sales order or order then it is sales order category.
                        - Do not change the user input when sending the response forward
                        Respond with: {"intent": "<intent>", "response": "<response>", "category": "<category_name_if_any>"}
                        
                        QUESTIONS, Answers = {
                        ("What products does Sales Navigator Online Store offer? Sales Navigator Online Store specializes in products like mechanical scales, digital scales, hardware tools, power tools, food processing machinery, agriculture tools and equipment, industrial tools and machinery, construction tools and materials, and automotive products."),
                        ("How long has Sales Navigator Online Store been in business? Sales Navigator Online Store, run by Fong Yuan Hung Import and Export Sdn. Bhd., has been serving customers since 1980."),
                        ("Where is Sales Navigator Online Store's market located? Our primary market is in East Malaysia, covering Sarawak and Sabah."),
                        ("From which countries does Sales Navigator Online Store import products? We import products from countries like China, Taiwan, South Korea, Thailand, Vietnam, the Philippines, India, the UK, Australia, and New Zealand."),
                        ("How can I contact Sales Navigator Online Store for more information? For support, email us at support@questmarketing.com.my. For business inquiries, use the contact details on our website."),
                        ("What is the annual import volume of Sales Navigator Online Store? We import approximately 10-15 containers (20 feet each) of goods annually."),
                        ("What product categories are available? We offer: Weighing Equipment, Agriculture Tools, Construction Materials, Industrial Machinery, General Hardware, Automotive Products."),
                        ("Can customers create an account on the website? Account creation is restricted to admins and salesmen only. Customers can browse and place orders without creating an account."),
                        ("What should I do if I forgot my password? Salesmen should contact the admin to reset their password at support@questmarketing.com.my."),
                        ("How do I change my password? Salesmen need to email the admin at support@questmarketing.com.my to request a password change."),
                        ("Who can access the admin features? Only authorized admins and salesmen can access admin features. Contact your admin for permissions.")
                        ("How do I place an order? Add products to your cart on our website and proceed to checkout. For assistance, contact our sales team."),
                        ("What are the payment methods available? We accept credit/debit cards, bank transfers, and online payment gateways."),
                        ("How can I track my order status? You'll receive a tracking number via email after placing an order. Use it to track your order on our website."),
                        ("What is your return and exchange policy? We offer returns and exchanges for defective or damaged products. Check our terms and conditions or contact support."),
                        ("How can I contact customer service? Email us at support@questmarketing.com.my or use the contact form on our website."),
                        ("Are there any shipping charges? Shipping charges depend on order size and destination. The cost is calculated during checkout."),
                        ("Do you ship internationally? Our primary market is East Malaysia, but we may accommodate international shipping requests. Contact customer service for details."),
                        ("Can I cancel or modify my order after placing it? You can modify or cancel orders within a limited timeframe. Contact customer service as soon as possible."),
                        ("What warranties do you offer on your products? Most products come with a manufacturer's warranty. Check product details or contact support for warranty information."),
                        ("How do I register an account on your website? Click on 'Sign In' and select 'Create an Account'. Follow the prompts to complete registration.")
                        ("How do I log in to the admin or salesman portal? The login portal is for admins and salesmen only. Click on 'Sign In' on the homepage and enter your credentials."),
                        ("Are there any promotions or discounts available? Yes, we offer regular promotions and discounts. Check the promotions page or contact our sales team."),
                        ("How can I check the availability of a specific product? Search for the product on our website or contact customer service with the product name or ID."),
                        ("Do you offer bulk purchase discounts? Yes, we provide bulk purchase discounts. Contact our sales team for details."),
                        ("Can I get a product demo or sample before purchasing? We may offer demos or samples for certain products. Contact our sales team to inquire."),
                        ("How do I become a distributor for Sales Navigator products? Fill out the distributor application on our website or contact our business development team.")
                    ]
                }
                    """
                },
                {"role": "user", "content": f"{user_message}"}
            ],
            max_tokens=100,
            temperature=0.3,
        )
        intent_response = gpt_intent_response['choices'][0]['message']['content'].strip()
        return json.loads(intent_response)
    except Exception as e:
        return {"intent": "general", "response": "Hello! How may I assist you today?"}


@app.route('/chat', methods=['POST'])
def handle_chat():
    try:
        user_message = request.json.get('message')
        selected_category = request.json.get('category')
        intent_data = detect_user_intent(user_message)
        intent = intent_data.get("intent")
        category = intent_data.get("category", None)
        loggedInUsername = request.json.get('username')
        
        if intent == "general":
            return jsonify({"response": intent_data.get("response")})
        elif intent == "sales_order":
            if selected_category == "sales_order":
                return sales_order_inquiry(loggedInUsername)
            else:
                return jsonify({"response": "It looks like you're asking about a sales order. Please switch to the 'Sales Order' category to proceed."})
        elif intent == "product_search":
            if selected_category == "search_product":
                search_term = user_message
                return search_products(search_term=search_term)
            else:
                return jsonify({"response": "It seems you're looking for a product. Please switch to the 'Product Search' category to proceed."})
        else:
            return jsonify({"response": "Sorry, I didn't understand that. Can you clarify?"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def preprocess_with_gpt(text):
    try:
        gpt_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """
                Extract product name, color, and attributes from queries.
                Return in format: {"product": "<name>", "color": "<color>", "other_attributes": "<attributes>"}
                """},
                {"role": "user", "content": f"Preprocess this text: {text}."}
            ],
            max_tokens=50,
            temperature=0.3,
        )
        cleaned_text = gpt_response['choices'][0]['message']['content'].strip()
        return cleaned_text
    except Exception as e:
        return text


def handle_search_with_products(product_name="", category_name=None, sub_category_name=None):
    search_keywords = preprocess_with_gpt(product_name)
    if not search_keywords:
        return "Error: Unable to process search query.", []

    try:
        extracted_data = json.loads(search_keywords)
        product_name = extracted_data['product']
        color = extracted_data.get('color')
        search_pattern = f"%{product_name}%"

        query = """
            SELECT
                p.id AS product_id,
                p.product_name,
                p.photo1,
                p.photo2,
                p.photo3,
                sc.sub_category AS sub_category_name,
                c.category AS category_name,
                b.brand AS brand_name
            FROM
                product p
            JOIN
                sub_category sc ON p.sub_category = sc.id
            JOIN
                category c ON sc.category = c.id
            JOIN
                brand b ON p.brand = b.id
            WHERE
                (LOWER(p.product_name) LIKE :search_pattern
                OR LOWER(c.category) LIKE :search_pattern
                OR LOWER(sc.sub_category) LIKE :search_pattern)
        """

        params = {'search_pattern': search_pattern}
        if color:
            query += " AND UPPER(p.product_name) LIKE :color"
            params['color'] = f"%{color}%"

        query += " ORDER BY p.product_name LIMIT 50;"
        result_set = db.session.execute(text(query), params).fetchall()

        matched_products = []
        for row in result_set:
            matched_products.append({
                'id': row[0],
                'product_name': row[1],
                'photo1': Product.get_photo_url(row[2]),
                'photo2': Product.get_photo_url(row[3]),
                'photo3': Product.get_photo_url(row[4]),
                'sub_category': row[5],
                'category': row[6],
                'brand_name': row[7]
            })

    except Exception as e:
        return f"Error: {str(e)}", []

    if not matched_products:
        all_products = Product.query.all()
        product_dicts = [product.to_dict() for product in all_products]
        matches = process.extract(product_name, [p['product_name'] for p in product_dicts], scorer=fuzz.partial_ratio)
        best_matches = [product_dicts[i] for match, score, i in matches if score > 70]
        if best_matches:
            matched_products.extend(best_matches)

    if not matched_products:
        return "It seems you're looking for Sales Order Inquiry. Please switch to the 'Sales Order Inquiry' category to proceed.", []

    return "Here are the products I found:", matched_products if matched_products else []


@app.route('/search', methods=['GET'])
def search_products(search_term=None):
    if not search_term:
        search_term = request.args.get('q', '')

    category_id = request.args.get('category_id')
    sub_category_id = request.args.get('sub_category_id')

    response_message, matched_products = handle_search_with_products(search_term, category_id, sub_category_id)

    return jsonify({
        "response": response_message,
        "products": matched_products if matched_products else []
    })


@app.route('/sales_order_inquiry', methods=['POST'])
def sales_order_inquiry(loggedInUsername):
    try:
        logging.debug("sales_order_inquiry endpoint called.")
        user_message = request.json.get('message')
        if not user_message:
            logging.error("No message received in request.")
            return jsonify({"error": "Message is required"}), 400

        # Log the received message
        logging.debug(f"User message received: {user_message}")

        # Use OpenAI to extract the relevant entities
        gpt_extraction_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
                    You are a SQL query generator. Your task is to take natural language queries from users and extract relevant entities in JSON format, and generate the appropriate SQL query to retrieve sales order information from a database.

                    ### The database has the following structure:

                    - `cart` table, which contains:
                    - `id` (the sales order ID),
                    - `created` (the date the order was created),
                    - `status` (e.g., "pending", "void", "confirm"),
                    - `customer_company_name` (the name of the customer’s company),
                    - `final_total` (the final total of the sales order),
                    - `order_option` (e.g., "Urgent", "Credit Term"),
                    - `buyer_area_name` (e.g., "Kuching", "KCH").

                    - `cart_item` table, which contains:
                    - `cart_id` (the ID of the sales order),
                    - `product_name` (the name of the product),
                    - `qty` (quantity of the product in the order: e.g., 15 if the user asks for "show me sales order with 15 hammer"),
                    - `unit_price` (unit price of the product),
                    - `total` (total price for the product).

                    ### Your task is to extract the following entities from the user’s query:

                    - **`status`**: The status of the sales order (e.g., "pending", "void", "confirm", "complete").
                    - **`limit`**: The number of distinct sales orders to return (e.g., 5 if the user asks for "5 sales orders").
                    - **`sort_order`**: The sorting direction for the sales orders:
                    - If the user asks for "first", use `asc` (ascending order).
                    - If the user asks for "last", use `desc` (descending order).
                    - **`product_name`**: The name of the product in the sales order, if specified.
                    - **`product_quantity`**: The quantity or qty of the product, if specified(e.g., 15 if the user asks for "show me sales order with 15 hammer").
                    - **`order_id`**: The ID of the sales order, if specified.
                    - **`company_name`**: The company name of the customer, if specified.
                    - **`total`**: The total amount of the sales order, if specified.
                    - **`buyer_area_name`**: The area name of the buyer (e.g., "Kuching", "KCH"), if specified.
                    - **`order_option`**: The order option (e.g., "Urgent", "Credit Term"), if specified.
                    - **`date`**: The date of the sales order, if specified.
                    - **`product_count`**: The number of different products in the order, if specified.

                    ### SQL Query Example:
                    - Extract relevant entities from user input and format it as:
                    {
                        "date": "2024-07-08",
                        "total": 232.3,
                        "company_name": "KCH Industrial Solutions",
                        "product_name": "Hammer",
                        "product_quantity": 15,
                        "order_id": 200,
                        "product_count": 10,
                        "status": "void",
                        "order_option": "Urgent",
                        "buyer_area_name": "Kuching",
                        "sort_order": "desc",  # or "asc"
                        "limit": 10  # if specified
                    }
                    If an entity is not present in the query, omit it from the JSON response.
                    """
                },
                {"role": "user", "content": f"Extract entities from this query: {user_message}."}
            ],
            max_tokens=150,
            temperature=0.7,
        )

        logging.debug("Received response from OpenAI GPT model.")

        # Extract entities from OpenAI response
        extracted_entities = gpt_extraction_response['choices'][0]['message']['content'].strip()
        logging.debug(f"Extracted entities from GPT: {extracted_entities}")

        try:
            # Sanitize the response to ensure it starts and ends with curly braces
            extracted_entities = gpt_extraction_response['choices'][0]['message']['content'].strip()
            # Attempt to parse the JSON
            entities = json.loads(extracted_entities)
            logging.debug(f"Parsed entities into JSON: {entities}")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode GPT response into JSON: {str(e)}")
            return jsonify({"error": "Failed to extract entities from user query"}), 400


        # Process the extracted entities like product search
        response_message, sales_orders = process_sales_order_query(entities, loggedInUsername)

        logging.debug(f"Sales order query result: {sales_orders}")

        return jsonify({"response": response_message, "sales_orders": sales_orders})

    except Exception as e:
        logging.error(f"Error in sales_order_inquiry: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

def process_sales_order_query(entities, loggedInUsername):
    try:
        logging.debug(f"Processing sales order query with entities: {entities}")
        conditions, params = [], {}

        # Add conditions based on extracted entities
        if 'status' in entities:
            logging.debug(f"Adding condition for status: {entities['status']}")
            conditions.append("LOWER(cart.status) = :status")
            params['status'] = entities['status'].lower()

        if 'total' in entities:
            tolerance = 0.5
            total = entities['total']
            logging.debug(f"Adding condition for total: {total}")
            conditions.append("cart.final_total BETWEEN :total_min AND :total_max")
            params['total_min'] = total - tolerance
            params['total_max'] = total + tolerance

        if 'date' in entities:
            logging.debug(f"Adding condition for date: {entities['date']}")
            conditions.append("DATE(cart.created) = :date")
            params['date'] = entities['date']

        if 'company_name' in entities:
            logging.debug(f"Adding condition for company name: {entities['company_name']}")
            conditions.append("LOWER(cart.customer_company_name) LIKE :company_name")
            params['company_name'] = f"%{entities['company_name'].lower()}%"

        if 'buyer_area_name' in entities:
            logging.debug(f"Adding condition for buyer area: {entities['buyer_area_name']}")
            conditions.append("LOWER(cart.buyer_area_name) LIKE :buyer_area_name")
            params['buyer_area_name'] = f"%{entities['buyer_area_name'].lower()}%"

        if 'order_option' in entities:
            logging.debug(f"Adding condition for order option: {entities['order_option']}")
            conditions.append("LOWER(cart.order_option) LIKE :order_option")
            params['order_option'] = f"%{entities['order_option'].lower()}%"

        if 'order_id' in entities:
            logging.debug(f"Adding condition for order ID: {entities['order_id']}")
            conditions.append("cart.id = :order_id")
            params['order_id'] = entities['order_id']

        if 'product_name' in entities:
            product_name = entities['product_name'].lower()
            logging.debug(f"Searching for product name matches: {product_name}")
            all_products_query = """
                SELECT DISTINCT LOWER(cart_item.product_name)
                FROM cart_item
            """
            all_products = db.session.execute(text(all_products_query)).fetchall()
            all_product_names = [row[0] for row in all_products]

            matches = process.extract(product_name, all_product_names, scorer=fuzz.partial_ratio, limit=5)
            matched_product_names = [match[0] for match in matches if match[1] > 90]
            logging.debug(f"Matched product names: {matched_product_names}")

            if matched_product_names:
                conditions.append("LOWER(cart_item.product_name) IN :product_names")
                params['product_names'] = tuple(matched_product_names)

        if 'product_count' in entities:
            logging.debug(f"Adding condition for product count: {entities['product_count']}")
            having_clause = "HAVING COUNT(cart_item.id) = :product_count"
            params['product_count'] = entities['product_count']
        else:
            having_clause = ""

        # Add condition for loggedInUsername
        conditions.append("salesman.username = :loggedInUsername")
        params['loggedInUsername'] = loggedInUsername

        # Construct query conditions string
        query_conditions = " AND ".join(conditions) if conditions else "1=1"
        limit = entities.get('limit', 10)
        sort_order = entities.get('sort_order', 'desc')

        # Construct the final query
        sql_query = f"""
            SELECT
                cart.id,
                cart.created,
                cart.status,
                cart.customer_company_name,
                cart.final_total,
                GROUP_CONCAT(cart_item.product_name) AS product_names,
                GROUP_CONCAT(cart_item.qty) AS quantities,
                GROUP_CONCAT(cart_item.unit_price) AS unit_prices,
                GROUP_CONCAT(cart_item.total) AS item_totals,
                cart.order_option,
                cart.buyer_area_name,
                salesman.username AS salesman_username
            FROM
                cart
            INNER JOIN
                cart_item ON cart.id = cart_item.cart_id
            INNER JOIN
                salesman ON cart.buyer_id = salesman.id
            WHERE
                {query_conditions}
            GROUP BY
                cart.id
            {having_clause}
            ORDER BY
                cart.created {sort_order}
            LIMIT :limit;
        """
        params['limit'] = limit


        logging.debug(f"Final SQL query: {sql_query} with params: {params}")

        result_set = db.session.execute(text(sql_query), params).fetchall()

        orders = []
        for row in result_set:
            row = dict(row._mapping)
            orders.append({
                'order_id': row['id'],
                'company_name': row['customer_company_name'],
                'created_date': row['created'].strftime('%Y-%m-%d'),
                'status': row['status'],
                'total': float(row['final_total']),
                'order_option': row['order_option'],
                'buyer_area_name': row['buyer_area_name'],
                'items': [{
                    'product_name': name,
                    'qty': int(qty),
                    'unit_price': float(price),
                    'total': float(total)
                } for name, qty, price, total in zip(row['product_names'].split(','), row['quantities'].split(','), row['unit_prices'].split(','), row['item_totals'].split(','))]
            })

        if not orders:
            logging.warning("No matching sales orders found.")
            return "No matching sales orders found.", []

        logging.debug(f"Found sales orders: {orders}")
        return "Here are the matching sales orders:", orders

    except Exception as e:
        logging.error(f"Error in processing sales order query: {str(e)}")
        return f"Error: {str(e)}", []



@app.route('/')
def index():
    return "Welcome to the GPT-4 Flask API! Use /chat to interact with the AI."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
