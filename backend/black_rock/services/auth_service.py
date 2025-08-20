"""
Black Rock Payment Terminal - Authentication Service
"""

import hashlib
import logging
import secrets
from typing import Optional, Dict, Any
from black_rock.models.database import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthService:
    """Handles merchant authentication for the payment terminal"""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize authentication service with database manager"""
        self.db_manager = db_manager
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple:
        """
        Hash a password with a salt
        
        Args:
            password: The password to hash
            salt: Optional salt (generated if not provided)
            
        Returns:
            tuple: (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Combine password and salt
        salted_password = password + salt
        
        # Hash the salted password
        hashed = hashlib.sha256(salted_password.encode()).hexdigest()
        
        return (hashed, salt)
    
    def register_merchant(self, merchant_name: str, email: str, password: str, 
                         merchant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Register a new merchant
        
        Args:
            merchant_name: Name of the merchant
            email: Merchant's email address
            password: Merchant's password
            merchant_id: Optional merchant ID (generated if not provided)
            
        Returns:
            Dict[str, Any]: Registration result
        """
        try:
            # Generate merchant ID if not provided
            if merchant_id is None:
                merchant_id = secrets.token_hex(8)
            
            # Hash password
            hashed_password, salt = self.hash_password(password)
            
            # Prepare merchant data
            merchant_data = {
                'merchant_id': merchant_id,
                'merchant_name': merchant_name,
                'email': email,
                'password_hash': f"{hashed_password}:{salt}",
                'bank_account': None,
                'crypto_wallet': None
            }
            
            # Save to database
            success = self.db_manager.add_merchant(merchant_data)
            
            if success:
                logger.info(f"Merchant {merchant_name} registered successfully")
                return {
                    'success': True,
                    'merchant_id': merchant_id,
                    'message': 'Merchant registered successfully'
                }
            else:
                logger.warning(f"Failed to register merchant {merchant_name}")
                return {
                    'success': False,
                    'message': 'Merchant registration failed. Email may already exist.'
                }
        except Exception as e:
            logger.error(f"Error during merchant registration: {str(e)}")
            return {
                'success': False,
                'message': f'Registration error: {str(e)}'
            }
    
    def authenticate_merchant(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a merchant
        
        Args:
            email: Merchant's email
            password: Merchant's password
            
        Returns:
            Dict[str, Any]: Authentication result
        """
        try:
            # Get merchant from database
            merchant = self.db_manager.get_merchant_by_email(email)
            
            if not merchant:
                logger.warning(f"Authentication failed: merchant with email {email} not found")
                return {
                    'success': False,
                    'message': 'Invalid email or password'
                }
            
            # Extract hash and salt
            password_hash, salt = merchant['password_hash'].split(':')
            
            # Hash provided password with stored salt
            hashed_password, _ = self.hash_password(password, salt)
            
            # Compare hashes
            if hashed_password == password_hash:
                logger.info(f"Merchant {email} authenticated successfully")
                return {
                    'success': True,
                    'merchant_id': merchant['merchant_id'],
                    'merchant_name': merchant['merchant_name'],
                    'message': 'Authentication successful'
                }
            else:
                logger.warning(f"Authentication failed: invalid password for {email}")
                return {
                    'success': False,
                    'message': 'Invalid email or password'
                }
        except Exception as e:
            logger.error(f"Error during merchant authentication: {str(e)}")
            return {
                'success': False,
                'message': f'Authentication error: {str(e)}'
            }
    
    def get_merchant_info(self, merchant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get merchant information
        
        Args:
            merchant_id: The merchant ID
            
        Returns:
            Optional[Dict[str, Any]]: Merchant information or None if not found
        """
        try:
            merchant = self.db_manager.get_merchant(merchant_id)
            if merchant:
                # Remove password hash from returned data
                merchant.pop('password_hash', None)
                return merchant
            return None
        except Exception as e:
            logger.error(f"Error retrieving merchant info: {str(e)}")
            return None
