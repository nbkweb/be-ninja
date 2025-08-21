""" 
Black Rock Payment Terminal - Flask API Application
"""

import os
import json
import logging
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import secrets

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
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Enable CORS
#CORS(app, supports_credentials=True)
CORS(app, supports_credentials=True, origins=["https://volvo-xc-90.onrender.com"])  #CORS Amendment

# Initialize services
db_manager = DatabaseManager()
auth_service = AuthService(db_manager)
payout_service = PayoutService(db_manager)
notification_service = NotificationService(db_manager)

# Initialize transaction processor
# In a real implementation, these would come from environment variables or config
processor = TransactionProcessor(
    merchant_id="default_merchant",
    terminal_id="default_terminal",
    server_url=os.environ.get('PAYMENT_SERVER_URL', 'http://localhost:5000')
)

# Start notification processing
notification_service.start_notification_processing()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Payment Terminal API is running'
    })

# ✅ New heartbeat route added here

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """Heartbeat endpoint for terminal monitoring"""
    try:
        # Check DB
        try:
            db_manager.test_connection()
            db_status = "ok"
        except Exception as e:
            logger.error(f"DB health check failed: {str(e)}")
            db_status = "error"

        # Check transaction processor
        try:
            processor_status = processor.get_terminal_status()
            processor_status_str = "ok" if processor_status else "error"
        except Exception as e:
            logger.error(f"Processor health check failed: {str(e)}")
            processor_status_str = "error"

        # Check notification service
        try:
            notif_status = "ok" if notification_service.is_alive() else "error"
        except Exception:
            notif_status = "unknown"

        # Return results
        return jsonify({
            'success': True,
            'status': 'alive',
            'components': {
                'database': db_status,
                'processor': processor_status_str,
                'notification_service': notif_status
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in heartbeat: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Heartbeat error: {str(e)}'
        }), 500
        
# ✅ End heartbeat route

@app.route('/api/register', methods=['POST'])
def register_merchant():
    """Register a new merchant"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        required_fields = ['merchant_name', 'email', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        result = auth_service.register_merchant(
            merchant_name=data['merchant_name'],
            email=data['email'],
            password=data['password']
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error in register_merchant: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Registration error: {str(e)}'
        }), 500

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
            # Store merchant ID in session
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

@app.route('/api/logout', methods=['POST'])
def logout_merchant():
    """Logout a merchant"""
    try:
        session.pop('merchant_id', None)
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error in logout_merchant: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Logout error: {str(e)}'
        }), 500

@app.route('/api/merchant/info', methods=['GET'])
def get_merchant_info():
    """Get merchant information"""
    try:
        # Check if merchant is logged in
        merchant_id = session.get('merchant_id')
        if not merchant_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        merchant_info = auth_service.get_merchant_info(merchant_id)
        
        if merchant_info:
            return jsonify({
                'success': True,
                'merchant': merchant_info
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Merchant not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error in get_merchant_info: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving merchant info: {str(e)}'
        }), 500

@app.route('/api/merchant/payout', methods=['GET'])
def get_merchant_payout_info():
    """Get merchant payout information"""
    try:
        # Check if merchant is logged in
        merchant_id = session.get('merchant_id')
        if not merchant_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        payout_info = payout_service.get_merchant_payout_info(merchant_id)
        
        if payout_info:
            return jsonify({
                'success': True,
                'payout_info': payout_info
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Merchant not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error in get_merchant_payout_info: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving payout info: {str(e)}'
        }), 500

@app.route('/api/protocols', methods=['GET'])
def get_protocols():
    """Get all available protocols"""
    try:
        from black_rock.config.settings import PROTOCOLS
        return jsonify({
            'success': True,
            'protocols': PROTOCOLS
        }), 200
    except Exception as e:
        logger.error(f"Error in get_protocols: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving protocols: {str(e)}'
        }), 500

@app.route('/api/transaction/process', methods=['POST'])
def process_transaction():
    """Process a payment transaction"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Check if merchant is logged in
        merchant_id = session.get('merchant_id')
        if not merchant_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        required_fields = ['amount', 'currency', 'transaction_type', 'payment_method', 'protocol']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Validate transaction type
        try:
            transaction_type = TransactionType(data['transaction_type'])
        except ValueError:
            return jsonify({
                'success': False,
                'message': f'Invalid transaction type: {data["transaction_type"]}'
            }), 400
        
        # Validate payment method
        try:
            payment_method = PaymentMethod(data['payment_method'])
        except ValueError:
            return jsonify({
                'success': False,
                'message': f'Invalid payment method: {data["payment_method"]}'
            }), 400
        
        # Validate protocol
        from black_rock.config.settings import PROTOCOLS
        if data['protocol'] not in PROTOCOLS:
            return jsonify({
                'success': False,
                'message': f'Invalid protocol: {data["protocol"]}'
            }), 400
        
        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({
                    'success': False,
                    'message': 'Amount must be positive'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid amount format'
            }), 400
        
        # Validate currency
        from black_rock.config.settings import SUPPORTED_CURRENCIES
        if data['currency'] not in SUPPORTED_CURRENCIES:
            return jsonify({
                'success': False,
                'message': f'Unsupported currency: {data["currency"]}'
            }), 400
        
        # Create transaction
        transaction = Transaction(
            amount=amount,
            currency=data['currency'],
            transaction_type=transaction_type,
            payment_method=payment_method,
            protocol=data['protocol'],
            merchant_id=merchant_id,
            terminal_id=processor.terminal_id,
            is_online=data.get('is_online', True)
        )
        
        # Set card data if provided
        if 'card_data' in data:
            transaction.set_card_data(data['card_data'])
        
        # Process transaction
        processed_transaction = processor.process_transaction(transaction)
        
        # Save transaction to database
        db_manager.save_transaction(processed_transaction.to_dict())
        
        # Create MTI notification
        if processed_transaction.mti:
            notification_service.create_mti_notification(
                processed_transaction.mti,
                processed_transaction.transaction_id,
                {
                    'status': processed_transaction.status.value,
                    'approval_code': processed_transaction.approval_code,
                    'response_code': processed_transaction.response_code,
                    'response_message': processed_transaction.response_message
                }
            )
        
        return jsonify({
            'success': True,
            'transaction': processed_transaction.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in process_transaction: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Transaction processing error: {str(e)}'
        }), 500

@app.route('/api/transaction/history', methods=['GET'])
def get_transaction_history():
    """Get transaction history for the authenticated merchant"""
    try:
        # Check if merchant is logged in
        merchant_id = session.get('merchant_id')
        if not merchant_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        transactions = db_manager.get_merchant_transactions(merchant_id)
        
        return jsonify({
            'success': True,
            'transactions': transactions
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_transaction_history: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving transaction history: {str(e)}'
        }), 500

@app.route('/api/transaction/<transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """Get a specific transaction by ID"""
    try:
        # Check if merchant is logged in
        merchant_id = session.get('merchant_id')
        if not merchant_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        transaction = db_manager.get_transaction(transaction_id)
        
        # Verify transaction belongs to merchant
        if transaction and transaction['merchant_id'] != merchant_id:
            return jsonify({
                'success': False,
                'message': 'Transaction not found'
            }), 404
        
        if transaction:
            return jsonify({
                'success': True,
                'transaction': transaction
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Transaction not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error in get_transaction: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving transaction: {str(e)}'
        }), 500

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get pending MTI notifications"""
    try:
        # Check if merchant is logged in
        merchant_id = session.get('merchant_id')
        if not merchant_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        notifications = notification_service.get_pending_notifications()
        
        # Filter notifications for this merchant
        merchant_notifications = [
            n for n in notifications 
            if db_manager.get_transaction(n['transaction_id'])['merchant_id'] == merchant_id
        ]
        
        return jsonify({
            'success': True,
            'notifications': merchant_notifications
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_notifications: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving notifications: {str(e)}'
        }), 500

@app.route('/api/payout/process', methods=['POST'])
def process_payout():
    """Process a payout to merchant's configured accounts"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Check if merchant is logged in
        merchant_id = session.get('merchant_id')
        if not merchant_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        required_fields = ['amount', 'currency', 'payout_method']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({
                    'success': False,
                    'message': 'Amount must be positive'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid amount format'
            }), 400
        
        # Validate currency
        from black_rock.config.settings import SUPPORTED_CURRENCIES
        if data['currency'] not in SUPPORTED_CURRENCIES:
            return jsonify({
                'success': False,
                'message': f'Unsupported currency: {data["currency"]}'
            }), 400
        
        # Process payout based on method
        if data['payout_method'] == 'bank':
            result = payout_service.process_bank_payout(
                merchant_id, amount, data['currency'], data.get('transaction_id', 'N/A')
            )
        elif data['payout_method'] == 'crypto':
            result = payout_service.process_crypto_payout(
                merchant_id, amount, data['currency'], data.get('transaction_id', 'N/A')
            )
        else:
            return jsonify({
                'success': False,
                'message': f'Invalid payout method: {data["payout_method"]}'
            }), 400
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error in process_payout: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Payout processing error: {str(e)}'
        }), 500

@app.route('/api/terminal/status', methods=['GET'])
def get_terminal_status():
    """Get terminal status"""
    try:
        # Check if merchant is logged in
        merchant_id = session.get('merchant_id')
        if not merchant_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        status = processor.get_terminal_status()
        
        return jsonify({
            'success': True,
            'terminal_status': status
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_terminal_status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving terminal status: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
