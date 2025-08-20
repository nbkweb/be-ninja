# Payment Terminal Backend

This is the backend service for the Black Rock Payment Terminal system. It provides a REST API for processing card payments, handling MTI (Message Type Indicator) messages, and managing payouts to bank accounts or cryptocurrency wallets.

## Features

- Merchant authentication (registration and login)
- Card payment processing with various protocols
- MTI message handling (0100, 0110, 0200, 0210, 0220, 0230)
- Real-time transaction notifications
- Bank account and cryptocurrency payout processing
- Transaction history management
- Offline transaction processing capabilities

## API Endpoints

### Authentication
- `POST /api/register` - Register a new merchant
- `POST /api/login` - Authenticate a merchant
- `POST /api/logout` - Logout a merchant
- `GET /api/merchant/info` - Get merchant information
- `GET /api/merchant/payout` - Get merchant payout information

### Protocols
- `GET /api/protocols` - Get all available protocols

### Transactions
- `POST /api/transaction/process` - Process a payment transaction
- `GET /api/transaction/history` - Get transaction history for merchant
- `GET /api/transaction/<transaction_id>` - Get specific transaction details

### Notifications
- `GET /api/notifications` - Get pending MTI notifications

### Payouts
- `POST /api/payout/process` - Process a payout to merchant's accounts
- `GET /api/terminal/status` - Get terminal status

## Deployment

This backend is configured for deployment on Render. To deploy:

1. Create a new Render service
2. Connect it to this repository
3. Configure environment variables as needed
4. Deploy!

## Environment Variables

- `SECRET_KEY` - Secret key for Flask sessions (generated automatically by Render)
- `PAYMENT_SERVER_URL` - URL of the upstream payment processor

## Dependencies

- Flask
- Flask-Cors
- requests

## Database

The backend uses SQLite for data storage. In production, this should be replaced with a more robust database solution.