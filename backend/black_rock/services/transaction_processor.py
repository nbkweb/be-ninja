"""
Black Rock Payment Terminal - Transaction Processor
"""

import json
import time
import logging
import datetime
import threading
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import queue
import requests
from requests.exceptions import RequestException

from black_rock.core.transaction import Transaction, TransactionStatus, TransactionType
from black_rock.handlers.protocol_handler import ProtocolFactory, ProtocolHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProcessorStatus(Enum):
    """Status of the transaction processor"""
    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"


class TransactionProcessor:
    """
    Handles transaction processing including online/offline modes,
    protocol handling, and server communication
    """
    
    def __init__(self, merchant_id: str, terminal_id: str, server_url: str):
        """Initialize the transaction processor"""
        self.merchant_id = merchant_id
        self.terminal_id = terminal_id
        self.server_url = server_url
        self.status = ProcessorStatus.IDLE
        self.offline_queue = queue.Queue()
        self.transaction_history = []
        self.is_online = True
        self.last_heartbeat = datetime.datetime.now()
        self.heartbeat_thread = None
        self.offline_sync_thread = None
        self.stop_threads = threading.Event()
        
        logger.info(f"Transaction processor initialized for merchant {merchant_id}, terminal {terminal_id}")
        
        # Start heartbeat thread
        self._start_heartbeat_thread()
    
    def _start_heartbeat_thread(self) -> None:
        """Start the heartbeat thread to monitor server connectivity"""
        def heartbeat_worker():
            while not self.stop_threads.is_set():
                try:
                    self._send_heartbeat()
                    time.sleep(60)  # Default heartbeat interval
                except Exception as e:
                    logger.error(f"Heartbeat error: {str(e)}")
                    time.sleep(10)  # Shorter interval for retry
        
        self.heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        logger.info("Heartbeat monitoring thread started")
    
    def _start_offline_sync_thread(self) -> None:
        """Start the offline transaction synchronization thread"""
        def offline_sync_worker():
            while not self.stop_threads.is_set():
                if self.is_online and not self.offline_queue.empty():
                    try:
                        transaction = self.offline_queue.get(block=False)
                        logger.info(f"Attempting to sync offline transaction {transaction.transaction_id}")
                        success = self._sync_offline_transaction(transaction)
                        if success:
                            logger.info(f"Successfully synced offline transaction {transaction.transaction_id}")
                        else:
                            logger.warning(f"Failed to sync offline transaction {transaction.transaction_id}, requeuing")
                            self.offline_queue.put(transaction)
                    except queue.Empty:
                        pass
                    except Exception as e:
                        logger.error(f"Error in offline sync: {str(e)}")
                time.sleep(30)  # Check every 30 seconds
        
        self.offline_sync_thread = threading.Thread(target=offline_sync_worker, daemon=True)
        self.offline_sync_thread.start()
        logger.info("Offline transaction sync thread started")
    
    def _send_heartbeat(self) -> None:
        """Send a heartbeat message to the server to check connectivity"""
        try:
            payload = {
                "terminal_id": self.terminal_id,
                "merchant_id": self.merchant_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "message_type": "heartbeat"
            }
            
            response = requests.post(
                f"{self.server_url}/heartbeat",
                json=payload,
                timeout=30  # Default timeout
            )
            
            if response.status_code == 200:
                self.is_online = True
                self.last_heartbeat = datetime.datetime.now()
                logger.debug("Heartbeat successful")
                
                # If we were offline before, log the reconnection
                if self.status == ProcessorStatus.OFFLINE:
                    logger.info("Terminal is back online")
                    self.status = ProcessorStatus.IDLE
                    
                    # Start offline sync if not already running
                    if not self.offline_sync_thread or not self.offline_sync_thread.is_alive():
                        self._start_offline_sync_thread()
            else:
                logger.warning(f"Heartbeat failed with status code {response.status_code}")
                self._handle_offline_mode()
                
        except RequestException as e:
            logger.warning(f"Heartbeat connection error: {str(e)}")
            self._handle_offline_mode()
        except Exception as e:
            logger.error(f"Unexpected error in heartbeat: {str(e)}")
            self._handle_offline_mode()
    
    def _handle_offline_mode(self) -> None:
        """Handle transition to offline mode"""
        if self.is_online:
            self.is_online = False
            self.status = ProcessorStatus.OFFLINE
            logger.warning("Terminal is now in OFFLINE mode")
    
    def _sync_offline_transaction(self, transaction: Transaction) -> bool:
        """
        Attempt to synchronize an offline transaction with the server
        Returns True if successful, False otherwise
        """
        try:
            # Prepare the transaction data for transmission
            payload = {
                "transaction": transaction.to_dict(),
                "terminal_id": self.terminal_id,
                "merchant_id": self.merchant_id,
                "sync_timestamp": datetime.datetime.now().isoformat()
            }
            
            response = requests.post(
                f"{self.server_url}/sync_offline",
                json=payload,
                timeout=30  # Default timeout
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "success":
                    # Update the transaction with server response if needed
                    if "server_approval_code" in response_data:
                        transaction.approval_code = response_data["server_approval_code"]
                    
                    logger.info(f"Offline transaction {transaction.transaction_id} successfully synced")
                    return True
                else:
                    logger.warning(f"Server rejected offline transaction: {response_data.get('message', 'Unknown error')}")
                    return False
            else:
                logger.warning(f"Offline sync failed with status code {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error syncing offline transaction: {str(e)}")
            return False
    
    def process_transaction(self, transaction: Transaction) -> Transaction:
        """
        Process a transaction either online or offline based on current connectivity
        and transaction requirements
        """
        self.status = ProcessorStatus.PROCESSING
        logger.info(f"Processing transaction {transaction.transaction_id}")
        
        # Check if this transaction type can be processed offline
        from black_rock.config.settings import PROTOCOLS
        protocol_info = PROTOCOLS[transaction.protocol]
        can_process_offline = not protocol_info["is_onledger"]
        
        # Determine if we should process online or offline
        should_process_online = self.is_online and (
            transaction.is_online or not can_process_offline
        )
        
        try:
            if should_process_online:
                logger.info(f"Processing transaction {transaction.transaction_id} ONLINE")
                self._process_online(transaction)
            else:
                if can_process_offline:
                    logger.info(f"Processing transaction {transaction.transaction_id} OFFLINE")
                    self._process_offline(transaction)
                else:
                    logger.warning(f"Transaction {transaction.transaction_id} requires online processing but terminal is offline")
                    transaction.update_status(
                        TransactionStatus.ERROR,
                        response_code="E1001",
                        response_message="Transaction requires online processing but terminal is offline"
                    )
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            transaction.update_status(
                TransactionStatus.ERROR,
                response_code="E9999",
                response_message=f"Internal error: {str(e)}"
            )
        finally:
            self.status = ProcessorStatus.IDLE if self.is_online else ProcessorStatus.OFFLINE
            
            # Add to transaction history
            self.transaction_history.append(transaction)
            
            return transaction
    
    def _process_online(self, transaction: Transaction) -> None:
        """Process a transaction online by communicating with the payment server"""
        # Set appropriate MTI based on transaction type
        if transaction.transaction_type == TransactionType.SALE:
            transaction.set_mti("0200")  # Financial Transaction Request
        elif transaction.transaction_type == TransactionType.REFUND:
            transaction.set_mti("0200")  # Financial Transaction Request (with refund indicator)
        elif transaction.transaction_type == TransactionType.VOID:
            transaction.set_mti("0200")  # Financial Transaction Request (with void indicator)
        elif transaction.transaction_type == TransactionType.PRE_AUTH:
            transaction.set_mti("0100")  # Authorization Request
        elif transaction.transaction_type == TransactionType.PRE_AUTH_COMPLETION:
            transaction.set_mti("0220")  # Financial Transaction Advice
        elif transaction.transaction_type == TransactionType.BALANCE_INQUIRY:
            transaction.set_mti("0100")  # Authorization Request (with balance inquiry indicator)
        
        # Update transaction status
        transaction.update_status(TransactionStatus.PROCESSING)
        
        # Prepare the request payload
        payload = {
            "mti": transaction.mti,
            "transaction": transaction.to_dict(),
            "terminal_id": self.terminal_id,
            "merchant_id": self.merchant_id,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Send the request to the server
        retry_count = 0
        max_retries = 3  # Default retry attempts
        
        while retry_count <= max_retries:
            try:
                response = requests.post(
                    f"{self.server_url}/process",
                    json=payload,
                    timeout=30  # Default timeout
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Process the response
                    if response_data.get("approved", False):
                        approval_code = response_data.get("approval_code")
                        if approval_code:
                            transaction.set_approval_code(approval_code)
                        else:
                            transaction.update_status(
                                TransactionStatus.ERROR,
                                response_code=response_data.get("response_code", "E2001"),
                                response_message="Missing approval code in approved transaction"
                            )
                    else:
                        transaction.update_status(
                            TransactionStatus.DECLINED,
                            response_code=response_data.get("response_code", "D0001"),
                            response_message=response_data.get("response_message", "Transaction declined")
                        )
                    
                    # Break out of retry loop on successful response
                    break
                    
                else:
                    logger.warning(f"Server returned status code {response.status_code}")
                    retry_count += 1
                    
                    if retry_count <= max_retries:
                        logger.info(f"Retrying transaction {transaction.transaction_id} (attempt {retry_count}/{max_retries})")
                        time.sleep(5)  # Default retry delay
                    else:
                        transaction.update_status(
                            TransactionStatus.ERROR,
                            response_code="E2002",
                            response_message=f"Server error: HTTP {response.status_code}"
                        )
                        
            except RequestException as e:
                logger.warning(f"Connection error: {str(e)}")
                retry_count += 1
                
                if retry_count <= max_retries:
                    logger.info(f"Retrying transaction {transaction.transaction_id} (attempt {retry_count}/{max_retries})")
                    time.sleep(5)  # Default retry delay
                else:
                    # If we've exhausted retries, check if we can process offline
                    from black_rock.config.settings import PROTOCOLS
                    protocol_info = PROTOCOLS[transaction.protocol]
                    if not protocol_info["is_onledger"]:
                        logger.info(f"Falling back to offline processing for transaction {transaction.transaction_id}")
                        self._process_offline(transaction)
                    else:
                        transaction.update_status(
                            TransactionStatus.ERROR,
                            response_code="E2003",
                            response_message=f"Connection error: {str(e)}"
                        )
                        self._handle_offline_mode()
                        
            except Exception as e:
                logger.error(f"Unexpected error in online processing: {str(e)}")
                transaction.update_status(
                    TransactionStatus.ERROR,
                    response_code="E9999",
                    response_message=f"Internal error: {str(e)}"
                )
                break
    
    def _process_offline(self, transaction: Transaction) -> None:
        """Process a transaction offline"""
        # Check if transaction amount exceeds offline limit
        offline_limit = 1000.00  # Default offline limit
        if transaction.amount > offline_limit:
            transaction.update_status(
                TransactionStatus.DECLINED,
                response_code="D2001",
                response_message=f"Transaction amount exceeds offline limit of {offline_limit} {transaction.currency}"
            )
            return
        
        # Create protocol handler to generate approval code
        handler = ProtocolFactory.create_handler(transaction.protocol)
        offline_code = handler.generate_approval_code(is_offline=True)
        
        transaction.set_approval_code(offline_code)
        transaction.update_status(TransactionStatus.OFFLINE_APPROVED)
        
        # Queue for later synchronization
        self.offline_queue.put(transaction)
        logger.info(f"Transaction {transaction.transaction_id} approved offline with code {offline_code}")
        
        # Make sure offline sync thread is running
        if not self.offline_sync_thread or not self.offline_sync_thread.is_alive():
            self._start_offline_sync_thread()
    
    def void_transaction(self, original_transaction_id: str) -> Optional[Transaction]:
        """
        Void a previous transaction
        Returns the void transaction if successful, None otherwise
        """
        # Find the original transaction
        original_transaction = None
        for transaction in self.transaction_history:
            if transaction.transaction_id == original_transaction_id:
                original_transaction = transaction
                break
        
        if not original_transaction:
            logger.warning(f"Cannot void: transaction {original_transaction_id} not found")
            return None
        
        # Check if transaction can be voided
        if original_transaction.status not in [TransactionStatus.APPROVED, TransactionStatus.OFFLINE_APPROVED]:
            logger.warning(f"Cannot void: transaction {original_transaction_id} is not in approved status")
            return None
        
        # Create a void transaction
        void_transaction = Transaction(
            amount=original_transaction.amount,
            currency=original_transaction.currency,
            transaction_type=TransactionType.VOID,
            payment_method=original_transaction.payment_method,
            protocol=original_transaction.protocol,
            merchant_id=self.merchant_id,
            terminal_id=self.terminal_id,
            is_online=self.is_online
        )
        
        # Set reference to original transaction
        void_transaction.card_data = original_transaction.card_data
        
        # Process the void
        return self.process_transaction(void_transaction)
    
    def get_transaction_history(self) -> List[Dict[str, Any]]:
        """Get transaction history as a list of dictionaries"""
        return [transaction.to_dict() for transaction in self.transaction_history]
    
    def get_offline_queue_size(self) -> int:
        """Get the number of transactions in the offline queue"""
        return self.offline_queue.qsize()
    
    def shutdown(self) -> None:
        """Shutdown the processor and stop all threads"""
        logger.info("Shutting down transaction processor")
        self.stop_threads.set()
        
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2.0)
        
        if self.offline_sync_thread:
            self.offline_sync_thread.join(timeout=2.0)
        
        logger.info("Transaction processor shutdown complete")
    
    def get_terminal_status(self) -> Dict[str, Any]:
        """
        Get the current terminal status
        
        Returns:
            Dict[str, Any]: Terminal status information
        """
        return {
            "merchant_id": self.merchant_id,
            "terminal_id": self.terminal_id,
            "online_status": "ONLINE" if self.is_online else "OFFLINE",
            "processor_status": self.status.value,
            "offline_queue_size": self.get_offline_queue_size(),
            "timestamp": datetime.datetime.now().isoformat()
        }
