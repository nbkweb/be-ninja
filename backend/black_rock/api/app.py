"""
Black Rock Payment Terminal - Flask API Application
"""

import os
import json
import logging
import secrets
from datetime import timedelta  # ✅ added for session config

from flask import Flask, request, jsonify, session
from flask_cors import CORS

# Internal Imports
from black_rock.models.database import DatabaseManager
from black_rock.services.auth_service import AuthService
from black_rock.services.payout_service import PayoutService
from black_rock.services.notification_service import NotificationService
from black_rock.services.transaction_processor import TransactionProcessor
from black_rock.core.transaction import Transaction, TransactionType, PaymentMethod
from black_rock.handlers.protocol_handler import ProtocolFactory, MTIHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# ✅ Use a fixed secret key from environment or fallback
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# ✅ Session cookie settings for cross-origin requests
app.config.update(
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    PERMANENT_SESSION_LIFETIME=timedelta(days=1)
)

# ✅ CORS enabled for frontend origin
CORS(app, supports_credentials=True, origins=["https://volvo-xc-90.onrender.com"])

# Initialize services
db_manager = DatabaseManager()
auth_service = AuthService(db_manager)
payout_service = PayoutService(db_manager)
notification_service = NotificationService(db_manager)

# Initialize transaction processor
processor = TransactionProcessor(
    merchant_id="default_merchant",
    terminal_id="default_terminal",
    server_url=os.environ.get('PAYMENT_SERVER_URL', 'http://localhost:5000')
)

# Start notification background thread
notification_service.start_notification_processing()

# Your existing login route
@app.route('/api/login', methods=['POST'])
def login_merchant():
    """Authenticate a merchant"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        required_fields = ['email', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        result = auth_service.authenticate_merchant(
            email=data['email'],
            password=data['password']
        )
        
        if result['success']:
            # ✅ Make session permanent so cookie stays alive
            session.permanent = True
            session['merchant_id'] = result['merchant_id']
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        logger.error(f"Error in login_merchant: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Authentication error: {str(e)}'
        }), 500


# === NEW: Add heartbeat route to avoid 404 and OFFLINE errors ===
@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    # Simply return a 200 OK with a JSON payload
    return jsonify({"status": "alive"}), 200


# === NEW: Add root URL route to avoid Not Found error on URL ===
@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "API is running"}), 200


# 🟢 All other routes stay unchanged (no edits needed)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
