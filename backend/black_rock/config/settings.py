"""
Black Rock Payment Terminal - Configuration Settings
"""

# Protocol definitions
PROTOCOLS = {
    "POS Terminal -101.1 (4-digit approval)": {
        "approval_length": 4,
        "is_onledger": True
    },
    "POS Terminal -101.4 (6-digit approval)": {
        "approval_length": 6,
        "is_onledger": True
    },
    "POS Terminal -101.6 (Pre-authorization)": {
        "approval_length": 6,
        "is_onledger": True
    },
    "POS Terminal -101.7 (4-digit approval)": {
        "approval_length": 4,
        "is_onledger": True
    },
    "POS Terminal -101.8 (PIN-LESS transaction)": {
        "approval_length": 4,
        "is_onledger": False
    },
    "POS Terminal -201.1 (6-digit approval)": {
        "approval_length": 6,
        "is_onledger": True
    },
    "POS Terminal -201.3 (6-digit approval)": {
        "approval_length": 6,
        "is_onledger": False
    },
    "POS Terminal -201.5 (6-digit approval)": {
        "approval_length": 6,
        "is_onledger": False
    }
}

# MTI Types
MTI_TYPES = {
    "0100": "Authorization Request",
    "0110": "Authorization Response",
    "0200": "Financial Transaction Request",
    "0210": "Financial Transaction Response",
    "0220": "Financial Transaction Advice",
    "0230": "Financial Transaction Advice Response",
    "0500": "Reversal Request",
    "0510": "Reversal Response"
}

# Supported currencies
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "BTC", "ETH"]

# Terminal settings
TERMINAL_SETTINGS = {
    "timeout_seconds": 30,
    "offline_transaction_limit": 1000.00,
    "batch_number": "001"
}

# Network settings
NETWORK_SETTINGS = {
    "server_url": "http://localhost:5000",
    "heartbeat_interval": 60,
    "retry_attempts": 3,
    "retry_delay": 5
}
