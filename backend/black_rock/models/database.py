"""
Black Rock Payment Terminal - Database Models
"""

import sqlite3
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database operations for the payment terminal"""
    
    def __init__(self, db_path: str = "payment_terminal.db"):
        """Initialize database manager"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self) -> None:
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create merchants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS merchants (
                merchant_id TEXT PRIMARY KEY,
                merchant_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                bank_account TEXT,
                crypto_wallet TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                protocol TEXT NOT NULL,
                merchant_id TEXT NOT NULL,
                terminal_id TEXT NOT NULL,
                is_online INTEGER NOT NULL,
                status TEXT NOT NULL,
                approval_code TEXT,
                response_code TEXT,
                response_message TEXT,
                mti TEXT,
                trace_number TEXT,
                batch_number TEXT,
                FOREIGN KEY (merchant_id) REFERENCES merchants (merchant_id)
            )
        ''')
        
        # Create MTI notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mti_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mti TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                processed INTEGER DEFAULT 0,
                FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def add_merchant(self, merchant_data: Dict[str, Any]) -> bool:
        """Add a new merchant to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO merchants 
                (merchant_id, merchant_name, email, password_hash, bank_account, crypto_wallet)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                merchant_data['merchant_id'],
                merchant_data['merchant_name'],
                merchant_data['email'],
                merchant_data['password_hash'],
                merchant_data.get('bank_account'),
                merchant_data.get('crypto_wallet')
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"Merchant {merchant_data['merchant_id']} added successfully")
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"Failed to add merchant: {str(e)}")
            return False
    
    def get_merchant(self, merchant_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve merchant information by merchant_id"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM merchants WHERE merchant_id = ?', (merchant_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_merchant_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve merchant information by email"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM merchants WHERE email = ?', (email,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def update_merchant_payout(self, merchant_id: str, bank_account: str = None, 
                              crypto_wallet: str = None) -> bool:
        """Update merchant payout information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if bank_account and crypto_wallet:
                cursor.execute('''
                    UPDATE merchants 
                    SET bank_account = ?, crypto_wallet = ?
                    WHERE merchant_id = ?
                ''', (bank_account, crypto_wallet, merchant_id))
            elif bank_account:
                cursor.execute('''
                    UPDATE merchants 
                    SET bank_account = ?
                    WHERE merchant_id = ?
                ''', (bank_account, merchant_id))
            elif crypto_wallet:
                cursor.execute('''
                    UPDATE merchants 
                    SET crypto_wallet = ?
                    WHERE merchant_id = ?
                ''', (crypto_wallet, merchant_id))
            
            conn.commit()
            conn.close()
            logger.info(f"Merchant {merchant_id} payout information updated")
            return True
        except Exception as e:
            logger.error(f"Failed to update merchant payout: {str(e)}")
            return False
    
    def save_transaction(self, transaction_data: Dict[str, Any]) -> bool:
        """Save transaction data to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO transactions 
                (transaction_id, timestamp, amount, currency, transaction_type, payment_method,
                 protocol, merchant_id, terminal_id, is_online, status, approval_code,
                 response_code, response_message, mti, trace_number, batch_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction_data['transaction_id'],
                transaction_data['timestamp'],
                transaction_data['amount'],
                transaction_data['currency'],
                transaction_data['transaction_type'],
                transaction_data['payment_method'],
                transaction_data['protocol'],
                transaction_data['merchant_id'],
                transaction_data['terminal_id'],
                int(transaction_data['is_online']),
                transaction_data['status'],
                transaction_data.get('approval_code'),
                transaction_data.get('response_code'),
                transaction_data.get('response_message'),
                transaction_data.get('mti'),
                transaction_data.get('trace_number'),
                transaction_data.get('batch_number')
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"Transaction {transaction_data['transaction_id']} saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save transaction: {str(e)}")
            return False
    
    def update_transaction(self, transaction_id: str, status: str, 
                          approval_code: str = None, response_code: str = None, 
                          response_message: str = None) -> bool:
        """Update transaction status and related information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if approval_code:
                cursor.execute('''
                    UPDATE transactions 
                    SET status = ?, approval_code = ?, response_code = ?, response_message = ?
                    WHERE transaction_id = ?
                ''', (status, approval_code, response_code, response_message, transaction_id))
            else:
                cursor.execute('''
                    UPDATE transactions 
                    SET status = ?, response_code = ?, response_message = ?
                    WHERE transaction_id = ?
                ''', (status, response_code, response_message, transaction_id))
            
            conn.commit()
            conn.close()
            logger.info(f"Transaction {transaction_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to update transaction: {str(e)}")
            return False
    
    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve transaction by transaction_id"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM transactions WHERE transaction_id = ?', (transaction_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_merchant_transactions(self, merchant_id: str) -> List[Dict[str, Any]]:
        """Retrieve all transactions for a merchant"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM transactions WHERE merchant_id = ? ORDER BY timestamp DESC', 
                      (merchant_id,))
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    def add_mti_notification(self, mti: str, transaction_id: str, message: str) -> bool:
        """Add an MTI notification to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO mti_notifications 
                (mti, transaction_id, message, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (mti, transaction_id, message, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            logger.info(f"MTI notification for transaction {transaction_id} added successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to add MTI notification: {str(e)}")
            return False
    
    def get_pending_mti_notifications(self) -> List[Dict[str, Any]]:
        """Retrieve all pending MTI notifications"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM mti_notifications WHERE processed = 0 ORDER BY timestamp ASC')
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    def mark_mti_notification_processed(self, notification_id: int) -> bool:
        """Mark an MTI notification as processed"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('UPDATE mti_notifications SET processed = 1 WHERE id = ?', 
                          (notification_id,))
            
            conn.commit()
            conn.close()
            logger.info(f"MTI notification {notification_id} marked as processed")
            return True
        except Exception as e:
            logger.error(f"Failed to mark MTI notification as processed: {str(e)}")
            return False
