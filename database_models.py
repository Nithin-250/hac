from typing import Dict, List, Optional
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages database connections and operations for the fraud detection system.
    Handles transactions, card locations, and fraud detection results.
    """
    
    def __init__(self, 
                 mongo_uri: str = "mongodb://localhost:27017/",
                 database_name: str = "fraud_detection"):
        self.mongo_uri = mongo_uri
        self.database_name = database_name
        self.client = None
        self.db = None
        
        # Collection names
        self.TRANSACTIONS_COLLECTION = "transactions"
        self.CARD_LOCATIONS_COLLECTION = "card_locations"
        self.FRAUD_ALERTS_COLLECTION = "fraud_alerts"
        self.BLACKLISTED_ACCOUNTS_COLLECTION = "blacklisted_accounts"
        
    def connect(self) -> bool:
        """
        Establish connection to MongoDB and create necessary indexes.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.database_name]
            
            # Test connection
            self.client.admin.command('ping')
            
            # Create indexes for better performance
            self._create_indexes()
            
            logger.info(f"Successfully connected to MongoDB database: {self.database_name}")
            return True
            
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def _create_indexes(self):
        """Create necessary indexes for optimal performance."""
        try:
            # Transactions collection indexes
            transactions_col = self.db[self.TRANSACTIONS_COLLECTION]
            transactions_col.create_index([("card_id", ASCENDING), ("timestamp", DESCENDING)])
            transactions_col.create_index([("recipient_account", ASCENDING)])
            transactions_col.create_index([("transaction_id", ASCENDING)], unique=True)
            
            # Card locations collection indexes
            locations_col = self.db[self.CARD_LOCATIONS_COLLECTION]
            locations_col.create_index([("card_id", ASCENDING)], unique=True)
            
            # Fraud alerts collection indexes
            alerts_col = self.db[self.FRAUD_ALERTS_COLLECTION]
            alerts_col.create_index([("transaction_id", ASCENDING)])
            alerts_col.create_index([("card_id", ASCENDING), ("timestamp", DESCENDING)])
            alerts_col.create_index([("fraud_type", ASCENDING)])
            
            # Blacklisted accounts collection indexes
            blacklist_col = self.db[self.BLACKLISTED_ACCOUNTS_COLLECTION]
            blacklist_col.create_index([("recipient_account", ASCENDING)], unique=True)
            blacklist_col.create_index([("status", ASCENDING)])
            
            logger.info("Database indexes created successfully")
            
        except PyMongoError as e:
            logger.error(f"Error creating indexes: {e}")
    
    def save_transaction(self, transaction_data: Dict) -> Dict:
        """
        Save a transaction to the database.
        
        Args:
            transaction_data: Dictionary containing transaction information
            
        Returns:
            Dictionary with save operation result
        """
        try:
            transactions_col = self.db[self.TRANSACTIONS_COLLECTION]
            
            # Add timestamp if not provided
            if 'timestamp' not in transaction_data:
                transaction_data['timestamp'] = datetime.now().isoformat()
            
            result = transactions_col.insert_one(transaction_data)
            
            if result.inserted_id:
                logger.info(f"Transaction {transaction_data.get('transaction_id')} saved successfully")
                return {
                    'success': True,
                    'transaction_id': transaction_data.get('transaction_id'),
                    'db_id': str(result.inserted_id)
                }
            else:
                return {'success': False, 'error': 'Failed to save transaction'}
                
        except PyMongoError as e:
            logger.error(f"Error saving transaction: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_historical_transactions(self, card_id: str, days: int = 30) -> List[Dict]:
        """
        Get historical transactions for a card.
        
        Args:
            card_id: Card identifier
            days: Number of days to look back
            
        Returns:
            List of transaction dictionaries
        """
        try:
            transactions_col = self.db[self.TRANSACTIONS_COLLECTION]
            
            # Calculate cutoff date
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            query = {
                'card_id': card_id,
                'timestamp': {'$gte': cutoff_date.isoformat()}
            }
            
            transactions = list(transactions_col.find(
                query,
                {'_id': 0}  # Exclude MongoDB ObjectId
            ).sort('timestamp', DESCENDING))
            
            return transactions
            
        except PyMongoError as e:
            logger.error(f"Error retrieving historical transactions: {e}")
            return []
    
    def update_card_location(self, location_data: Dict) -> Dict:
        """
        Update the trusted location for a card.
        
        Args:
            location_data: Dictionary containing location information
            
        Returns:
            Dictionary with update operation result
        """
        try:
            locations_col = self.db[self.CARD_LOCATIONS_COLLECTION]
            
            # Add timestamp if not provided
            if 'updated_at' not in location_data:
                location_data['updated_at'] = datetime.now().isoformat()
            
            result = locations_col.update_one(
                {'card_id': location_data['card_id']},
                {'$set': location_data},
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                logger.info(f"Location updated for card {location_data['card_id']}")
                return {
                    'success': True,
                    'card_id': location_data['card_id'],
                    'action': 'upserted' if result.upserted_id else 'updated'
                }
            else:
                return {'success': False, 'error': 'Failed to update location'}
                
        except PyMongoError as e:
            logger.error(f"Error updating card location: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_card_location(self, card_id: str) -> Optional[Dict]:
        """
        Get the current trusted location for a card.
        
        Args:
            card_id: Card identifier
            
        Returns:
            Dictionary with location information or None
        """
        try:
            locations_col = self.db[self.CARD_LOCATIONS_COLLECTION]
            
            location = locations_col.find_one(
                {'card_id': card_id},
                {'_id': 0}  # Exclude MongoDB ObjectId
            )
            
            return location
            
        except PyMongoError as e:
            logger.error(f"Error retrieving card location: {e}")
            return None
    
    def save_fraud_alert(self, alert_data: Dict) -> Dict:
        """
        Save a fraud alert to the database.
        
        Args:
            alert_data: Dictionary containing fraud alert information
            
        Returns:
            Dictionary with save operation result
        """
        try:
            alerts_col = self.db[self.FRAUD_ALERTS_COLLECTION]
            
            # Add timestamp if not provided
            if 'alert_timestamp' not in alert_data:
                alert_data['alert_timestamp'] = datetime.now().isoformat()
            
            result = alerts_col.insert_one(alert_data)
            
            if result.inserted_id:
                logger.warning(f"Fraud alert saved for transaction {alert_data.get('transaction_id')}")
                return {
                    'success': True,
                    'alert_id': str(result.inserted_id),
                    'transaction_id': alert_data.get('transaction_id')
                }
            else:
                return {'success': False, 'error': 'Failed to save fraud alert'}
                
        except PyMongoError as e:
            logger.error(f"Error saving fraud alert: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_fraud_alerts(self, card_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Get fraud alerts from the database.
        
        Args:
            card_id: Optional card ID to filter alerts
            limit: Maximum number of alerts to return
            
        Returns:
            List of fraud alert dictionaries
        """
        try:
            alerts_col = self.db[self.FRAUD_ALERTS_COLLECTION]
            
            query = {}
            if card_id:
                query['card_id'] = card_id
            
            alerts = list(alerts_col.find(
                query,
                {'_id': 0}  # Exclude MongoDB ObjectId
            ).sort('alert_timestamp', DESCENDING).limit(limit))
            
            return alerts
            
        except PyMongoError as e:
            logger.error(f"Error retrieving fraud alerts: {e}")
            return []
    
    def get_database_stats(self) -> Dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            stats = {
                'database_name': self.database_name,
                'collections': {}
            }
            
            collection_names = [
                self.TRANSACTIONS_COLLECTION,
                self.CARD_LOCATIONS_COLLECTION,
                self.FRAUD_ALERTS_COLLECTION,
                self.BLACKLISTED_ACCOUNTS_COLLECTION
            ]
            
            for collection_name in collection_names:
                collection = self.db[collection_name]
                count = collection.count_documents({})
                stats['collections'][collection_name] = {
                    'document_count': count
                }
            
            stats['last_updated'] = datetime.now().isoformat()
            return stats
            
        except PyMongoError as e:
            logger.error(f"Error getting database stats: {e}")
            return {'error': str(e)}

# Transaction data model structure for reference
TRANSACTION_MODEL = {
    'transaction_id': str,  # Unique transaction identifier
    'card_id': str,  # Card identifier
    'amount': float,  # Transaction amount
    'recipient_account': str,  # Recipient account number
    'latitude': float,  # Transaction location latitude
    'longitude': float,  # Transaction location longitude
    'location_name': str,  # Human-readable location name
    'timestamp': str,  # ISO format timestamp
    'merchant_id': str,  # Optional merchant identifier
    'transaction_type': str,  # Optional transaction type
}

# Card location data model structure for reference
CARD_LOCATION_MODEL = {
    'card_id': str,  # Card identifier (unique)
    'trusted_latitude': float,  # Current trusted latitude
    'trusted_longitude': float,  # Current trusted longitude
    'trusted_location_name': str,  # Current trusted location name
    'last_update_transaction_id': str,  # Transaction that updated this location
    'last_update_timestamp': str,  # When location was last updated
    'updated_at': str,  # System update timestamp
}

# Fraud alert data model structure for reference
FRAUD_ALERT_MODEL = {
    'transaction_id': str,  # Transaction that triggered the alert
    'card_id': str,  # Card involved in the fraud
    'fraud_type': str,  # Type of fraud detected
    'severity': str,  # Alert severity (low, medium, high)
    'details': dict,  # Detailed fraud detection results
    'alert_timestamp': str,  # When alert was created
    'status': str,  # Alert status (active, resolved, false_positive)
}