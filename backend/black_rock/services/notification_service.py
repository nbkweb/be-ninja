"""
Black Rock Payment Terminal - MTI Notification Service
"""

import logging
import json
import threading
import time
from typing import Dict, Any, List
from black_rock.models.database import DatabaseManager
from black_rock.handlers.protocol_handler import MTIHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationService:
    """Handles MTI message notifications and processing"""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize notification service with database manager"""
        self.db_manager = db_manager
        self.notification_callbacks = []
        self.processing_thread = None
        self.stop_event = threading.Event()
        
    def add_notification_callback(self, callback) -> None:
        """
        Add a callback function to be notified when MTI messages are processed
        
        Args:
            callback: Function to call when notifications are available
        """
        self.notification_callbacks.append(callback)
        logger.info("Notification callback added")
    
    def remove_notification_callback(self, callback) -> None:
        """
        Remove a callback function
        
        Args:
            callback: Function to remove
        """
        if callback in self.notification_callbacks:
            self.notification_callbacks.remove(callback)
            logger.info("Notification callback removed")
    
    def start_notification_processing(self) -> None:
        """Start the notification processing thread"""
        def processing_worker():
            while not self.stop_event.is_set():
                try:
                    # Get pending notifications
                    pending_notifications = self.db_manager.get_pending_mti_notifications()
                    
                    if pending_notifications:
                        # Notify all callbacks
                        for callback in self.notification_callbacks:
                            try:
                                callback(pending_notifications)
                            except Exception as e:
                                logger.error(f"Error in notification callback: {str(e)}")
                        
                        # Mark notifications as processed
                        for notification in pending_notifications:
                            self.db_manager.mark_mti_notification_processed(notification['id'])
                    
                    # Wait before next check
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"Error in notification processing: {str(e)}")
                    time.sleep(10)
        
        self.processing_thread = threading.Thread(target=processing_worker, daemon=True)
        self.processing_thread.start()
        logger.info("Notification processing thread started")
    
    def stop_notification_processing(self) -> None:
        """Stop the notification processing thread"""
        self.stop_event.set()
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        logger.info("Notification processing thread stopped")
    
    def create_mti_notification(self, mti: str, transaction_id: str, 
                              additional_data: Dict[str, Any] = None) -> bool:
        """
        Create an MTI notification
        
        Args:
            mti: The MTI code
            transaction_id: The transaction ID
            additional_data: Optional additional data to include in the notification
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate MTI
            if not MTIHandler.validate_mti(mti):
                logger.warning(f"Invalid MTI code: {mti}")
                return False
            
            # Get MTI description
            description = MTIHandler.get_mti_description(mti)
            
            # Prepare notification message
            message_data = {
                'mti': mti,
                'description': description,
                'transaction_id': transaction_id
            }
            
            if additional_data:
                message_data.update(additional_data)
            
            message = json.dumps(message_data)
            
            # Save notification to database
            success = self.db_manager.add_mti_notification(mti, transaction_id, message)
            
            if success:
                logger.info(f"MTI notification {mti} created for transaction {transaction_id}")
                return True
            else:
                logger.warning(f"Failed to create MTI notification {mti} for transaction {transaction_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating MTI notification: {str(e)}")
            return False
    
    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """
        Get all pending MTI notifications
        
        Returns:
            List[Dict[str, Any]]: List of pending notifications
        """
        try:
            return self.db_manager.get_pending_mti_notifications()
        except Exception as e:
            logger.error(f"Error retrieving pending notifications: {str(e)}")
            return []
