"""
Black Rock Payment Terminal - Core Transaction Module
"""

import uuid
import datetime
import logging
from enum import Enum
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TransactionType(Enum):
    """Transaction types supported by the terminal"""
    SALE = "SALE"
    REFUND = "REFUND"
    VOID = "VOID"
    PRE_AUTH = "PRE_AUTH"
    PRE_AUTH_COMPLETION = "PRE_AUTH_COMPLETION"
    BALANCE_INQUIRY = "BALANCE_INQUIRY"


class TransactionStatus(Enum):
    """Possible transaction statuses"""
    INITIALIZED = "INITIALIZED"
    PROCESSING = "PROCESSING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    OFFLINE_APPROVED = "OFFLINE_APPROVED"
    PENDING = "PENDING"


class PaymentMethod(Enum):
    """Payment methods supported by the terminal"""
    CARD_SWIPE = "CARD_SWIPE"
    CARD_DIP = "CARD_DIP"
    CARD_NFC = "CARD_NFC"
    MANUAL_ENTRY = "MANUAL_ENTRY"


class Transaction:
    """Base transaction class for all payment transactions"""
    
    def __init__(
        self,
        amount: float,
        currency: str,
        transaction_type: TransactionType,
        payment_method: PaymentMethod,
        protocol: str,
        merchant_id: str,
        terminal_id: str,
        is_online: bool = True
    ):
        """Initialize a new transaction"""
        self.transaction_id = str(uuid.uuid4())
        self.timestamp = datetime.datetime.now()
        self.amount = amount
        self.currency = currency
        self.transaction_type = transaction_type
        self.payment_method = payment_method
        self.protocol = protocol
        self.merchant_id = merchant_id
        self.terminal_id = terminal_id
        self.is_online = is_online
        self.status = TransactionStatus.INITIALIZED
        self.approval_code = None
        self.response_code = None
        self.response_message = None
        self.card_data = {}
        self.mti = None
        self.trace_number = None
        self.batch_number = None
        
        # Validate protocol
        from black_rock.config.settings import PROTOCOLS
        if protocol not in PROTOCOLS:
            raise ValueError(f"Invalid protocol: {protocol}")
        
        # Validate currency
        from black_rock.config.settings import SUPPORTED_CURRENCIES
        if currency not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {currency}")
        
        # Generate trace number (unique within a batch)
        self.trace_number = self._generate_trace_number()
        from black_rock.config.settings import TERMINAL_SETTINGS
        self.batch_number = TERMINAL_SETTINGS["batch_number"]
        
        logger.info(f"Transaction {self.transaction_id} initialized: {transaction_type.value} "
                   f"for {amount} {currency} using {payment_method.value}")
    
    def _generate_trace_number(self) -> str:
        """Generate a unique trace number for the transaction"""
        # Simple implementation - in production this would be more sophisticated
        return str(int(datetime.datetime.now().timestamp() * 1000) % 1000000).zfill(6)
    
    def set_card_data(self, card_data: Dict[str, Any]) -> None:
        """Set card data for the transaction"""
        # In a real implementation, this would include encryption/tokenization
        self.card_data = card_data
        logger.info(f"Card data set for transaction {self.transaction_id}")
    
    def set_mti(self, mti: str) -> None:
        """Set the Message Type Indicator for the transaction"""
        from black_rock.config.settings import MTI_TYPES
        if mti not in MTI_TYPES:
            raise ValueError(f"Invalid MTI: {mti}")
        self.mti = mti
        logger.info(f"MTI set to {mti} for transaction {self.transaction_id}")
    
    def update_status(self, status: TransactionStatus, response_code: str = None, 
                     response_message: str = None) -> None:
        """Update the transaction status"""
        self.status = status
        if response_code:
            self.response_code = response_code
        if response_message:
            self.response_message = response_message
        logger.info(f"Transaction {self.transaction_id} status updated to {status.value}")
    
    def set_approval_code(self, approval_code: str) -> None:
        """Set the approval code for the transaction"""
        from black_rock.config.settings import PROTOCOLS
        protocol_info = PROTOCOLS[self.protocol]
        expected_length = protocol_info["approval_length"]
        
        if len(approval_code) != expected_length:
            raise ValueError(f"Invalid approval code length. Expected {expected_length} digits.")
        
        self.approval_code = approval_code
        self.update_status(TransactionStatus.APPROVED)
        logger.info(f"Approval code {approval_code} set for transaction {self.transaction_id}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary for storage or transmission"""
        return {
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp.isoformat(),
            "amount": self.amount,
            "currency": self.currency,
            "transaction_type": self.transaction_type.value,
            "payment_method": self.payment_method.value,
            "protocol": self.protocol,
            "merchant_id": self.merchant_id,
            "terminal_id": self.terminal_id,
            "is_online": self.is_online,
            "status": self.status.value,
            "approval_code": self.approval_code,
            "response_code": self.response_code,
            "response_message": self.response_message,
            "mti": self.mti,
            "trace_number": self.trace_number,
            "batch_number": self.batch_number
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create a transaction object from a dictionary"""
        transaction = cls(
            amount=data["amount"],
            currency=data["currency"],
            transaction_type=TransactionType(data["transaction_type"]),
            payment_method=PaymentMethod(data["payment_method"]),
            protocol=data["protocol"],
            merchant_id=data["merchant_id"],
            terminal_id=data["terminal_id"],
            is_online=data["is_online"]
        )
        
        transaction.transaction_id = data["transaction_id"]
        transaction.timestamp = datetime.datetime.fromisoformat(data["timestamp"])
        transaction.status = TransactionStatus(data["status"])
        transaction.approval_code = data["approval_code"]
        transaction.response_code = data["response_code"]
        transaction.response_message = data["response_message"]
        transaction.mti = data["mti"]
        transaction.trace_number = data["trace_number"]
        transaction.batch_number = data["batch_number"]
        
        return transaction
