from typing import Dict, List, Optional
from datetime import datetime
import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)

class AutoBlacklistManager:
    """
    Manages automatic blacklisting of fraudulent recipient accounts in MongoDB.
    When a transaction is found fraudulent due to the recipient account,
    that account is added to the blacklist to prevent future transactions.
    """
    
    def __init__(self, 
                 mongo_uri: str = "mongodb://localhost:27017/",
                 database_name: str = "fraud_detection",
                 blacklist_collection: str = "blacklisted_accounts"):
        self.mongo_uri = mongo_uri
        self.database_name = database_name
        self.blacklist_collection = blacklist_collection
        self.client = None
        self.db = None
        self.blacklist_col = None
        
    def connect(self) -> bool:
        """
        Establish connection to MongoDB.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.database_name]
            self.blacklist_col = self.db[self.blacklist_collection]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            return True
            
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def add_to_blacklist(self, 
                        recipient_account: str,
                        reason: str,
                        fraud_type: str,
                        transaction_id: str,
                        card_id: str,
                        amount: float,
                        additional_info: Optional[Dict] = None) -> Dict:
        """
        Add a recipient account to the blacklist.
        
        Args:
            recipient_account: Account number/ID to blacklist
            reason: Reason for blacklisting
            fraud_type: Type of fraud detected (e.g., "statistical_anomaly", "geographical_drift")
            transaction_id: ID of the fraudulent transaction
            card_id: Card involved in the fraud
            amount: Transaction amount
            additional_info: Additional information about the fraud
            
        Returns:
            Dictionary with blacklist operation result
        """
        if not self.blacklist_col:
            logger.error("MongoDB connection not established")
            return {'success': False, 'error': 'Database connection not available'}
        
        # Check if account is already blacklisted
        existing_entry = self.blacklist_col.find_one({'recipient_account': recipient_account})
        
        if existing_entry:
            # Update existing entry with new fraud incident
            update_data = {
                '$push': {
                    'fraud_incidents': {
                        'transaction_id': transaction_id,
                        'card_id': card_id,
                        'amount': amount,
                        'fraud_type': fraud_type,
                        'reason': reason,
                        'timestamp': datetime.now().isoformat(),
                        'additional_info': additional_info or {}
                    }
                },
                '$set': {
                    'last_fraud_date': datetime.now().isoformat(),
                    'fraud_count': existing_entry.get('fraud_count', 0) + 1
                }
            }
            
            try:
                result = self.blacklist_col.update_one(
                    {'recipient_account': recipient_account},
                    update_data
                )
                
                if result.modified_count > 0:
                    logger.warning(f"Updated blacklist entry for account {recipient_account} "
                                 f"(fraud count: {existing_entry.get('fraud_count', 0) + 1})")
                    return {
                        'success': True,
                        'action': 'updated',
                        'recipient_account': recipient_account,
                        'fraud_count': existing_entry.get('fraud_count', 0) + 1
                    }
                else:
                    return {'success': False, 'error': 'Failed to update blacklist entry'}
                    
            except PyMongoError as e:
                logger.error(f"Error updating blacklist entry: {e}")
                return {'success': False, 'error': str(e)}
        
        else:
            # Create new blacklist entry
            blacklist_entry = {
                'recipient_account': recipient_account,
                'first_fraud_date': datetime.now().isoformat(),
                'last_fraud_date': datetime.now().isoformat(),
                'fraud_count': 1,
                'status': 'active',
                'fraud_incidents': [{
                    'transaction_id': transaction_id,
                    'card_id': card_id,
                    'amount': amount,
                    'fraud_type': fraud_type,
                    'reason': reason,
                    'timestamp': datetime.now().isoformat(),
                    'additional_info': additional_info or {}
                }],
                'created_at': datetime.now().isoformat()
            }
            
            try:
                result = self.blacklist_col.insert_one(blacklist_entry)
                
                if result.inserted_id:
                    logger.warning(f"Added account {recipient_account} to blacklist due to {fraud_type}")
                    return {
                        'success': True,
                        'action': 'created',
                        'recipient_account': recipient_account,
                        'blacklist_id': str(result.inserted_id)
                    }
                else:
                    return {'success': False, 'error': 'Failed to insert blacklist entry'}
                    
            except PyMongoError as e:
                logger.error(f"Error creating blacklist entry: {e}")
                return {'success': False, 'error': str(e)}
    
    def is_blacklisted(self, recipient_account: str) -> Dict:
        """
        Check if a recipient account is blacklisted.
        
        Args:
            recipient_account: Account number/ID to check
            
        Returns:
            Dictionary with blacklist status
        """
        if not self.blacklist_col:
            logger.error("MongoDB connection not established")
            return {'is_blacklisted': False, 'error': 'Database connection not available'}
        
        try:
            blacklist_entry = self.blacklist_col.find_one({
                'recipient_account': recipient_account,
                'status': 'active'
            })
            
            if blacklist_entry:
                return {
                    'is_blacklisted': True,
                    'recipient_account': recipient_account,
                    'fraud_count': blacklist_entry.get('fraud_count', 0),
                    'first_fraud_date': blacklist_entry.get('first_fraud_date'),
                    'last_fraud_date': blacklist_entry.get('last_fraud_date'),
                    'reason': 'Account blacklisted due to previous fraudulent transactions'
                }
            else:
                return {
                    'is_blacklisted': False,
                    'recipient_account': recipient_account,
                    'reason': 'Account not found in blacklist'
                }
                
        except PyMongoError as e:
            logger.error(f"Error checking blacklist status: {e}")
            return {'is_blacklisted': False, 'error': str(e)}
    
    def remove_from_blacklist(self, recipient_account: str, reason: str = "Manual removal") -> Dict:
        """
        Remove an account from the blacklist (deactivate).
        
        Args:
            recipient_account: Account number/ID to remove
            reason: Reason for removal
            
        Returns:
            Dictionary with removal operation result
        """
        if not self.blacklist_col:
            logger.error("MongoDB connection not established")
            return {'success': False, 'error': 'Database connection not available'}
        
        try:
            result = self.blacklist_col.update_one(
                {'recipient_account': recipient_account, 'status': 'active'},
                {
                    '$set': {
                        'status': 'inactive',
                        'removal_reason': reason,
                        'removed_at': datetime.now().isoformat()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Removed account {recipient_account} from blacklist: {reason}")
                return {
                    'success': True,
                    'recipient_account': recipient_account,
                    'reason': reason
                }
            else:
                return {
                    'success': False,
                    'error': 'Account not found in active blacklist'
                }
                
        except PyMongoError as e:
            logger.error(f"Error removing from blacklist: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_blacklist_summary(self) -> Dict:
        """
        Get summary statistics of the blacklist.
        
        Returns:
            Dictionary with blacklist statistics
        """
        if not self.blacklist_col:
            logger.error("MongoDB connection not established")
            return {'error': 'Database connection not available'}
        
        try:
            total_active = self.blacklist_col.count_documents({'status': 'active'})
            total_inactive = self.blacklist_col.count_documents({'status': 'inactive'})
            
            # Get fraud type distribution
            pipeline = [
                {'$match': {'status': 'active'}},
                {'$unwind': '$fraud_incidents'},
                {'$group': {
                    '_id': '$fraud_incidents.fraud_type',
                    'count': {'$sum': 1}
                }}
            ]
            
            fraud_types = list(self.blacklist_col.aggregate(pipeline))
            fraud_type_distribution = {item['_id']: item['count'] for item in fraud_types}
            
            return {
                'total_active_blacklisted': total_active,
                'total_inactive_blacklisted': total_inactive,
                'fraud_type_distribution': fraud_type_distribution,
                'last_updated': datetime.now().isoformat()
            }
            
        except PyMongoError as e:
            logger.error(f"Error getting blacklist summary: {e}")
            return {'error': str(e)}
    
    def get_blacklisted_accounts(self, limit: int = 100) -> List[Dict]:
        """
        Get list of blacklisted accounts.
        
        Args:
            limit: Maximum number of accounts to return
            
        Returns:
            List of blacklisted account dictionaries
        """
        if not self.blacklist_col:
            logger.error("MongoDB connection not established")
            return []
        
        try:
            accounts = list(self.blacklist_col.find(
                {'status': 'active'},
                {'_id': 0}  # Exclude MongoDB ObjectId
            ).limit(limit).sort('last_fraud_date', -1))
            
            return accounts
            
        except PyMongoError as e:
            logger.error(f"Error retrieving blacklisted accounts: {e}")
            return []