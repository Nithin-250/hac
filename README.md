# 🔍 Advanced Fraud Detection System

A comprehensive fraud detection system that identifies suspicious transactions using multiple detection methods including statistical anomaly detection, geographical drift analysis, and automatic blacklisting mechanisms.

## 🚀 Features

### 1. 📊 Statistical Anomaly Detection
- **Z-Score Analysis**: Uses numpy to calculate Z-scores for transaction amounts
- **Threshold**: Flags transactions with Z-score > 2.5 as abnormal spikes
- **Historical Analysis**: Analyzes transaction patterns over configurable time periods (default: 30 days)
- **Adaptive Learning**: Continuously updates statistical baselines as new transactions are processed

### 2. 📍 Geographical Drift Detection
- **Distance Calculation**: Uses Haversine formula to calculate distances between transaction locations
- **Threshold**: Flags transactions when distance > 500 km from last known location
- **Location Tracking**: Maintains trusted location history for each card
- **Auto-Update**: Updates trusted location after confirmed geographical shifts
- **Example**: Detects if a card is used in Chennai then suddenly in Delhi

### 3. 🛑 Auto-Blacklist Mechanism
- **Automatic Blacklisting**: Adds fraudulent recipient accounts to MongoDB blacklist
- **Incident Tracking**: Maintains detailed fraud incident history for each blacklisted account
- **Prevention**: Blocks future transactions to blacklisted accounts
- **Fraud Count**: Tracks number of fraud incidents per account

## 🏗️ Architecture

```
fraud_detection_service.py          # Main service coordinator
├── statistical_anomaly_detector.py # Z-score based anomaly detection
├── geographical_drift_detector.py  # Location-based fraud detection
├── auto_blacklist_manager.py       # Blacklist management
└── database_models.py              # MongoDB data models and operations
```

## 📋 Requirements

- Python 3.7+
- MongoDB 4.0+
- See `requirements.txt` for Python dependencies

## ⚡ Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start MongoDB

```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or install MongoDB locally
# https://docs.mongodb.com/manual/installation/
```

### 3. Run the Demo

```bash
python example_usage.py
```

## 💻 Usage Examples

### Basic Transaction Analysis

```python
from fraud_detection_service import FraudDetectionService

# Initialize the service
fraud_service = FraudDetectionService(
    mongo_uri="mongodb://localhost:27017/",
    database_name="fraud_detection",
    z_score_threshold=2.5,
    distance_threshold_km=500.0
)

# Connect to database
fraud_service.connect()

# Analyze a transaction
transaction = {
    'transaction_id': 'TXN001',
    'card_id': 'CARD_12345',
    'amount': 5000.00,  # Potentially anomalous amount
    'recipient_account': 'ACC_SUSPICIOUS_001',
    'latitude': 28.7041,  # Delhi
    'longitude': 77.1025,
    'location_name': 'Delhi',
    'timestamp': '2024-01-15T14:30:00'
}

result = fraud_service.analyze_transaction(transaction)

if result['is_fraudulent']:
    print(f"🚨 FRAUD DETECTED!")
    print(f"Fraud Types: {result['fraud_types']}")
    print(f"Fraud Score: {result['fraud_score']}")
else:
    print("✅ Transaction appears legitimate")

# Disconnect
fraud_service.disconnect()
```

### Batch Processing

```python
# Analyze multiple transactions
transactions = [transaction1, transaction2, transaction3]
results = fraud_service.batch_analyze_transactions(transactions)

for result in results:
    print(f"Transaction {result['transaction_id']}: {'FRAUD' if result['is_fraudulent'] else 'OK'}")
```

## 📊 Detection Methods

### Statistical Anomaly Detection

**How it works:**
1. Collects historical transaction amounts for the card (last 30 days)
2. Calculates mean and standard deviation using numpy
3. Computes Z-score: `(current_amount - mean) / std_dev`
4. Flags transactions with `|Z-score| > 2.5`

**Example:**
- Historical amounts: [100, 150, 120, 180, 200]
- Mean: 150, Std Dev: 37.4
- New transaction: 500
- Z-score: (500 - 150) / 37.4 = 9.36 > 2.5 ✅ **FLAGGED**

### Geographical Drift Detection

**How it works:**
1. Retrieves last known location for the card
2. Calculates great-circle distance using Haversine formula
3. Flags transactions if distance > 500 km
4. Updates trusted location after confirmed drift

**Example:**
- Last location: Chennai (13.0827°N, 80.2707°E)
- Current location: Delhi (28.7041°N, 77.1025°E)
- Distance: ~1,759 km > 500 km ✅ **FLAGGED**

### Auto-Blacklist Mechanism

**How it works:**
1. When fraud is detected, recipient account is automatically blacklisted
2. Future transactions to blacklisted accounts are immediately flagged
3. Maintains fraud incident history and statistics
4. Supports manual blacklist management

## 🗄️ Database Schema

### Collections

#### `transactions`
```javascript
{
  "_id": ObjectId,
  "transaction_id": "TXN001",
  "card_id": "CARD_12345",
  "amount": 150.00,
  "recipient_account": "ACC_001",
  "latitude": 13.0827,
  "longitude": 80.2707,
  "location_name": "Chennai",
  "timestamp": "2024-01-15T14:30:00"
}
```

#### `blacklisted_accounts`
```javascript
{
  "_id": ObjectId,
  "recipient_account": "ACC_SUSPICIOUS_001",
  "status": "active",
  "fraud_count": 2,
  "first_fraud_date": "2024-01-15T14:30:00",
  "last_fraud_date": "2024-01-16T10:15:00",
  "fraud_incidents": [
    {
      "transaction_id": "TXN001",
      "fraud_type": "statistical_anomaly",
      "amount": 5000.00,
      "timestamp": "2024-01-15T14:30:00"
    }
  ]
}
```

#### `fraud_alerts`
```javascript
{
  "_id": ObjectId,
  "transaction_id": "TXN001",
  "card_id": "CARD_12345",
  "fraud_type": "statistical_anomaly, geographical_drift",
  "severity": "high",
  "details": { /* detailed analysis results */ },
  "status": "active"
}
```

#### `card_locations`
```javascript
{
  "_id": ObjectId,
  "card_id": "CARD_12345",
  "trusted_latitude": 13.0827,
  "trusted_longitude": 80.2707,
  "trusted_location_name": "Chennai",
  "last_update_transaction_id": "TXN005",
  "updated_at": "2024-01-15T14:30:00"
}
```

## ⚙️ Configuration

### Service Configuration

```python
fraud_service = FraudDetectionService(
    mongo_uri="mongodb://localhost:27017/",
    database_name="fraud_detection",
    z_score_threshold=2.5,        # Statistical anomaly threshold
    distance_threshold_km=500.0,  # Geographical drift threshold
    lookback_days=30              # Historical data window
)
```

### Environment Variables

Create a `.env` file:

```env
MONGODB_URI=mongodb://localhost:27017/
DATABASE_NAME=fraud_detection
Z_SCORE_THRESHOLD=2.5
DISTANCE_THRESHOLD_KM=500.0
LOOKBACK_DAYS=30
```

## 📈 Fraud Scoring

The system calculates a fraud score based on multiple factors:

- **Blacklisted Account**: +100 points (maximum)
- **Statistical Anomaly**: +20 × Z-score (capped at 80 points)
- **Geographical Drift**: +distance_km ÷ 10 (capped at 60 points)

### Severity Levels

- **High**: Score ≥ 80
- **Medium**: Score ≥ 40
- **Low**: Score < 40

## 🔧 API Reference

### FraudDetectionService

#### Methods

- `connect()` - Establish database connections
- `disconnect()` - Close database connections
- `analyze_transaction(transaction)` - Analyze single transaction
- `batch_analyze_transactions(transactions)` - Analyze multiple transactions
- `get_service_status()` - Get service status and statistics

### StatisticalAnomalyDetector

#### Methods

- `calculate_z_score(amount, historical_amounts)` - Calculate Z-score
- `is_anomalous_transaction(card_id, amount, historical_transactions)` - Check for anomalies
- `get_transaction_statistics(card_id, historical_transactions)` - Get statistical summary

### GeographicalDriftDetector

#### Methods

- `haversine_distance(lat1, lon1, lat2, lon2)` - Calculate distance between coordinates
- `detect_geographical_drift(card_id, lat, lon, location, historical_transactions)` - Detect location drift
- `update_trusted_location(card_id, lat, lon, location, transaction_id, timestamp)` - Update trusted location

### AutoBlacklistManager

#### Methods

- `add_to_blacklist(recipient_account, reason, fraud_type, ...)` - Add account to blacklist
- `is_blacklisted(recipient_account)` - Check if account is blacklisted
- `remove_from_blacklist(recipient_account, reason)` - Remove from blacklist
- `get_blacklist_summary()` - Get blacklist statistics

## 🧪 Testing

Run the example demo to test all functionality:

```bash
python example_usage.py
```

The demo will:
1. Create sample transactions with various fraud patterns
2. Analyze each transaction for fraud
3. Demonstrate statistical anomaly detection
4. Show geographical drift detection
5. Test automatic blacklisting
6. Display comprehensive results

## 📊 Sample Output

```
🔍 Fraud Detection System Demo
==================================================

📡 Connecting to services...
✅ Successfully connected to fraud detection service

🔍 Analyzing Transaction 4/6
   ID: TXN004
   Card: CARD_12345
   Amount: $5000.00
   Location: Chennai
   Recipient: ACC_SUSPICIOUS_001
   🚨 FRAUD DETECTED!
   Fraud Types: statistical_anomaly
   Fraud Score: 187.2
   📊 Statistical Anomaly: Z-score = 9.36
   ✅ Account ACC_SUSPICIOUS_001 added to blacklist

🔍 Analyzing Transaction 5/6
   ID: TXN005
   Card: CARD_12345
   Amount: $300.00
   Location: Delhi
   Recipient: ACC_DISTANT_001
   🚨 FRAUD DETECTED!
   Fraud Types: geographical_drift
   Fraud Score: 175.9
   📍 Geographical Drift: 1759km from Chennai
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For questions or issues:
1. Check the example usage script
2. Review the API documentation
3. Open an issue on GitHub

---

**Built with ❤️ for secure financial transactions**
