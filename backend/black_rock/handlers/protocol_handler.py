"""
Black Rock Payment Terminal - Protocol Handlers
"""

import logging
import datetime
import random
import string
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

from black_rock.core.transaction import Transaction, TransactionStatus, TransactionType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProtocolHandler:
    """Base class for protocol handlers"""
    
    def __init__(self, protocol_name: str):
        """Initialize the protocol handler"""
        from black_rock.config.settings import PROTOCOLS
        if protocol_name not in PROTOCOLS:
            raise ValueError(f"Invalid protocol: {protocol_name}")
        
        self.protocol_name = protocol_name
        self.protocol_config = PROTOCOLS[protocol_name]
        self.approval_length = self.protocol_config["approval_length"]
        self.is_onledger = self.protocol_config["is_onledger"]
        
        logger.info(f"Initialized protocol handler for {protocol_name}")
    
    def validate_approval_code(self, approval_code: str) -> bool:
        """
        Validate an approval code for this protocol
        
        Args:
            approval_code: The approval code to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Check length
        if len(approval_code) != self.approval_length:
            logger.warning(f"Invalid approval code length: expected {self.approval_length}, got {len(approval_code)}")
            return False
        
        # For offline codes, they should start with "OF"
        if approval_code.startswith("OF") and not self.is_onledger:
            # Rest should be digits
            if not approval_code[2:].isdigit():
                logger.warning("Invalid offline approval code format: should be 'OF' followed by digits")
                return False
            return True
        
        # For online codes, they should be all digits or alphanumeric depending on protocol
        if self.is_onledger:
            if self.protocol_name.startswith("POS Terminal -101"):
                # 101.x protocols use numeric approval codes
                if not approval_code.isdigit():
                    logger.warning("Invalid online approval code format for 101.x protocol: should be all digits")
                    return False
            elif self.protocol_name.startswith("POS Terminal -201"):
                # 201.x protocols use alphanumeric approval codes
                if not all(c.isalnum() for c in approval_code):
                    logger.warning("Invalid online approval code format for 201.x protocol: should be alphanumeric")
                    return False
            
            return True
        
        logger.warning("Invalid approval code format")
        return False
    
    def generate_approval_code(self, is_offline: bool = False) -> str:
        """
        Generate an approval code for this protocol
        
        Args:
            is_offline: Whether to generate an offline approval code
            
        Returns:
            str: The generated approval code
        """
        if is_offline and not self.is_onledger:
            # Generate offline approval code
            digits = ''.join(random.choices(string.digits, k=self.approval_length - 2))
            return f"OF{digits}"
        
        # Generate online approval code
        if self.protocol_name.startswith("POS Terminal -101"):
            # 101.x protocols use numeric approval codes
            return ''.join(random.choices(string.digits, k=self.approval_length))
        elif self.protocol_name.startswith("POS Terminal -201"):
            # 201.x protocols use alphanumeric approval codes
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=self.approval_length))
        
        # Default to numeric
        return ''.join(random.choices(string.digits, k=self.approval_length))
    
    def prepare_transaction_data(self, transaction: Transaction) -> Dict[str, Any]:
        """
        Prepare transaction data for transmission according to protocol
        
        Args:
            transaction: The transaction to prepare
            
        Returns:
            Dict[str, Any]: The prepared transaction data
        """
        # Base transaction data
        data = {
            "protocol": self.protocol_name,
            "mti": transaction.mti,
            "transaction_id": transaction.transaction_id,
            "timestamp": transaction.timestamp.isoformat(),
            "amount": transaction.amount,
            "currency": transaction.currency,
            "merchant_id": transaction.merchant_id,
            "terminal_id": transaction.terminal_id,
            "trace_number": transaction.trace_number,
            "batch_number": transaction.batch_number
        }
        
        # Add protocol-specific fields
        if self.protocol_name == "POS Terminal -101.1 (4-digit approval)":
            data["approval_code_format"] = "numeric"
            data["approval_length"] = 4
            data["requires_online"] = True
            
        elif self.protocol_name == "POS Terminal -101.4 (6-digit approval)":
            data["approval_code_format"] = "numeric"
            data["approval_length"] = 6
            data["requires_online"] = True
            
        elif self.protocol_name == "POS Terminal -101.6 (Pre-authorization)":
            data["approval_code_format"] = "numeric"
            data["approval_length"] = 6
            data["requires_online"] = True
            data["is_preauth"] = True
            
        elif self.protocol_name == "POS Terminal -101.7 (4-digit approval)":
            data["approval_code_format"] = "numeric"
            data["approval_length"] = 4
            data["requires_online"] = True
            
        elif self.protocol_name == "POS Terminal -101.8 (PIN-LESS transaction)":
            data["approval_code_format"] = "numeric"
            data["approval_length"] = 4
            data["requires_online"] = False
            data["is_pinless"] = True
            
        elif self.protocol_name == "POS Terminal -201.1 (6-digit approval)":
            data["approval_code_format"] = "alphanumeric"
            data["approval_length"] = 6
            data["requires_online"] = True
            
        elif self.protocol_name == "POS Terminal -201.3 (6-digit approval)":
            data["approval_code_format"] = "alphanumeric"
            data["approval_length"] = 6
            data["requires_online"] = False
            
        elif self.protocol_name == "POS Terminal -201.5 (6-digit approval)":
            data["approval_code_format"] = "alphanumeric"
            data["approval_length"] = 6
            data["requires_online"] = False
        
        return data
    
    def parse_response(self, response_data: Dict[str, Any], transaction: Transaction) -> None:
        """
        Parse a response from the server and update the transaction
        
        Args:
            response_data: The response data from the server
            transaction: The transaction to update
        """
        # Check if the response is valid for this protocol
        if "protocol" in response_data and response_data["protocol"] != self.protocol_name:
            logger.warning(f"Protocol mismatch: expected {self.protocol_name}, got {response_data['protocol']}")
            transaction.update_status(
                TransactionStatus.ERROR,
                response_code="E3001",
                response_message="Protocol mismatch in response"
            )
            return
        
        # Check if the transaction was approved
        if "approved" in response_data and response_data["approved"]:
            # Check if approval code is present and valid
            if "approval_code" in response_data:
                approval_code = response_data["approval_code"]
                if self.validate_approval_code(approval_code):
                    transaction.set_approval_code(approval_code)
                else:
                    transaction.update_status(
                        TransactionStatus.ERROR,
                        response_code="E3002",
                        response_message="Invalid approval code in response"
                    )
            else:
                transaction.update_status(
                    TransactionStatus.ERROR,
                    response_code="E3003",
                    response_message="Missing approval code in approved response"
                )
        else:
            # Transaction was declined
            transaction.update_status(
                TransactionStatus.DECLINED,
                response_code=response_data.get("response_code", "D0001"),
                response_message=response_data.get("response_message", "Transaction declined")
            )


class ProtocolFactory:
    """Factory for creating protocol handlers"""
    
    @staticmethod
    def create_handler(protocol_name: str) -> ProtocolHandler:
        """
        Create a protocol handler for the specified protocol
        
        Args:
            protocol_name: The name of the protocol
            
        Returns:
            ProtocolHandler: The protocol handler
        """
        from black_rock.config.settings import PROTOCOLS
        if protocol_name not in PROTOCOLS:
            raise ValueError(f"Invalid protocol: {protocol_name}")
        
        # For now, we use the base ProtocolHandler for all protocols
        # In a real implementation, we might have specialized handlers for each protocol
        return ProtocolHandler(protocol_name)


class MTIHandler:
    """Handler for Message Type Indicator (MTI) messages"""
    
    @staticmethod
    def validate_mti(mti: str) -> bool:
        """
        Validate an MTI
        
        Args:
            mti: The MTI to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        from black_rock.config.settings import MTI_TYPES
        return mti in MTI_TYPES
    
    @staticmethod
    def get_mti_description(mti: str) -> str:
        """
        Get the description of an MTI
        
        Args:
            mti: The MTI
            
        Returns:
            str: The MTI description
        """
        from black_rock.config.settings import MTI_TYPES
        if mti in MTI_TYPES:
            return MTI_TYPES[mti]
        return "Unknown MTI"
    
    @staticmethod
    def get_response_mti(request_mti: str) -> str:
        """
        Get the response MTI for a request MTI
        
        Args:
            request_mti: The request MTI
            
        Returns:
            str: The response MTI
        """
        mti_map = {
            "0100": "0110",  # Authorization Request -> Authorization Response
            "0200": "0210",  # Financial Transaction Request -> Financial Transaction Response
            "0220": "0230",  # Financial Transaction Advice -> Financial Transaction Advice Response
            "0500": "0510",  # Reversal Request -> Reversal Response
        }
        
        if request_mti in mti_map:
            return mti_map[request_mti]
        
        # Default to same MTI if no mapping found
        return request_mti
    
    @staticmethod
    def get_mti_for_transaction_type(transaction_type: TransactionType, is_response: bool = False) -> str:
        """
        Get the appropriate MTI for a transaction type
        
        Args:
            transaction_type: The transaction type
            is_response: Whether this is a response MTI
            
        Returns:
            str: The MTI
        """
        mti_map = {
            TransactionType.SALE: "0200",
            TransactionType.REFUND: "0200",
            TransactionType.VOID: "0200",
            TransactionType.PRE_AUTH: "0100",
            TransactionType.PRE_AUTH_COMPLETION: "0220",
            TransactionType.BALANCE_INQUIRY: "0100"
        }
        
        if transaction_type in mti_map:
            mti = mti_map[transaction_type]
            if is_response:
                return MTIHandler.get_response_mti(mti)
            return mti
        
        # Default to financial transaction request
        return "0200" if not is_response else "0210"
