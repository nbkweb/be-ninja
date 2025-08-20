"""
Simple test script to verify transaction processing functionality
"""

import sys
import os

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from black_rock.core.transaction import Transaction, TransactionType, PaymentMethod
from black_rock.handlers.protocol_handler import ProtocolFactory, MTIHandler
from black_rock.services.transaction_processor import TransactionProcessor

def test_transaction_creation():
    """Test creating a transaction"""
    print("Testing transaction creation...")
    
    transaction = Transaction(
        amount=100.50,
        currency="USD",
        transaction_type=TransactionType.SALE,
        payment_method=PaymentMethod.MANUAL_ENTRY,
        protocol="POS Terminal -101.1 (4-digit approval)",
        merchant_id="test_merchant_123",
        terminal_id="test_terminal_456"
    )
    
    print(f"Transaction ID: {transaction.transaction_id}")
    print(f"Amount: {transaction.amount} {transaction.currency}")
    print(f"Type: {transaction.transaction_type.value}")
    print(f"Protocol: {transaction.protocol}")
    print(f"Status: {transaction.status.value}")
    print()

def test_protocol_handler():
    """Test protocol handler functionality"""
    print("Testing protocol handler...")
    
    handler = ProtocolFactory.create_handler("POS Terminal -101.4 (6-digit approval)")
    
    # Test approval code generation
    approval_code = handler.generate_approval_code()
    print(f"Generated approval code: {approval_code}")
    
    # Test approval code validation
    is_valid = handler.validate_approval_code(approval_code)
    print(f"Approval code validation: {is_valid}")
    
    # Test MTI handling
    mti = MTIHandler.get_mti_for_transaction_type(TransactionType.SALE)
    print(f"MTI for SALE transaction: {mti}")
    
    response_mti = MTIHandler.get_response_mti(mti)
    print(f"Response MTI: {response_mti}")
    print()

def test_mti_handler():
    """Test MTI handler functionality"""
    print("Testing MTI handler...")
    
    # Test MTI validation
    valid_mti = "0200"
    invalid_mti = "9999"
    
    print(f"MTI {valid_mti} is valid: {MTIHandler.validate_mti(valid_mti)}")
    print(f"MTI {invalid_mti} is valid: {MTIHandler.validate_mti(invalid_mti)}")
    
    # Test MTI description
    print(f"MTI {valid_mti} description: {MTIHandler.get_mti_description(valid_mti)}")
    print()

if __name__ == "__main__":
    print("Payment Terminal Transaction Test")
    print("=" * 35)
    
    # Test transaction creation
    test_transaction_creation()
    
    # Test protocol handler
    test_protocol_handler()
    
    # Test MTI handler
    test_mti_handler()
    
    print("Transaction tests completed.")