from typing import Dict, List, Optional
from datetime import datetime
import logging

from statistical_anomaly_detector import StatisticalAnomalyDetector
from geographical_drift_detector import GeographicalDriftDetector
from auto_blacklist_manager import AutoBlacklistManager
from database_models import DatabaseManager

logger = logging.getLogger(__name__)

class FraudDetectionService:
    """
    Main fraud detection service that integrates:
    1. Statistical anomaly detection (Z-score > 2.5)
    2. Geographical drift detection (distance > 500km)
    3. Auto-blacklist mechanism for fraudulent accounts
    """
    
    def __init__(self, 
                 mongo_uri: str = "mongodb://localhost:27017/",
                 database_name: str = "fraud_detection",
                 z_score_threshold: float = 2.5,
                 distance_threshold_km: float = 500.0,
                 lookback_days: int = 30):
        
        # Initialize components
        self.anomaly_detector = StatisticalAnomalyDetector(
            z_score_threshold=z_score_threshold,
            lookback_days=lookback_days
        )
        
        self.drift_detector = GeographicalDriftDetector(
            distance_threshold_km=distance_threshold_km
        )
        
        self.blacklist_manager = AutoBlacklistManager(
            mongo_uri=mongo_uri,
            database_name=database_name
        )
        
        self.db_manager = DatabaseManager(
            mongo_uri=mongo_uri,
            database_name=database_name
        )
        
        # Configuration
        self.config = {
            'z_score_threshold': z_score_threshold,
            'distance_threshold_km': distance_threshold_km,
            'lookback_days': lookback_days,
            'database_name': database_name
        }
        
        self.is_connected = False
    
    def connect(self) -> bool:
        """
        Establish connections to all services.
        
        Returns:
            True if all connections successful, False otherwise
        """
        try:
            # Connect to database
            if not self.db_manager.connect():
                logger.error("Failed to connect to database")
                return False
            
            # Connect to blacklist manager
            if not self.blacklist_manager.connect():
                logger.error("Failed to connect to blacklist manager")
                return False
            
            self.is_connected = True
            logger.info("Fraud detection service connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting fraud detection service: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from all services."""
        self.db_manager.disconnect()
        self.blacklist_manager.disconnect()
        self.is_connected = False
        logger.info("Fraud detection service disconnected")
    
    def analyze_transaction(self, transaction: Dict) -> Dict:
        """
        Analyze a transaction for fraud using all detection methods.
        
        Args:
            transaction: Dictionary containing transaction data
            
        Returns:
            Dictionary with comprehensive fraud analysis results
        """
        if not self.is_connected:
            return {
                'error': 'Service not connected to database',
                'transaction_id': transaction.get('transaction_id')
            }
        
        transaction_id = transaction.get('transaction_id')
        card_id = transaction.get('card_id')
        amount = transaction.get('amount')
        recipient_account = transaction.get('recipient_account')
        latitude = transaction.get('latitude')
        longitude = transaction.get('longitude')
        location_name = transaction.get('location_name', 'Unknown')
        
        logger.info(f"Analyzing transaction {transaction_id} for card {card_id}")
        
        # Initialize results
        fraud_analysis = {
            'transaction_id': transaction_id,
            'card_id': card_id,
            'amount': amount,
            'recipient_account': recipient_account,
            'location': location_name,
            'analysis_timestamp': datetime.now().isoformat(),
            'is_fraudulent': False,
            'fraud_types': [],
            'fraud_score': 0.0,
            'details': {}
        }
        
        # Step 1: Check if recipient account is blacklisted
        blacklist_check = self.blacklist_manager.is_blacklisted(recipient_account)
        fraud_analysis['details']['blacklist_check'] = blacklist_check
        
        if blacklist_check.get('is_blacklisted', False):
            fraud_analysis['is_fraudulent'] = True
            fraud_analysis['fraud_types'].append('blacklisted_recipient')
            fraud_analysis['fraud_score'] += 100  # Maximum score for blacklisted accounts
            logger.warning(f"Transaction {transaction_id} flagged: recipient account {recipient_account} is blacklisted")
        
        # Step 2: Statistical anomaly detection
        try:
            historical_transactions = self.db_manager.get_historical_transactions(
                card_id, self.config['lookback_days']
            )
            
            anomaly_result = self.anomaly_detector.is_anomalous_transaction(
                card_id, amount, historical_transactions
            )
            fraud_analysis['details']['statistical_anomaly'] = anomaly_result
            
            if anomaly_result.get('is_anomalous', False):
                fraud_analysis['is_fraudulent'] = True
                fraud_analysis['fraud_types'].append('statistical_anomaly')
                # Score based on Z-score magnitude (higher Z-score = higher fraud score)
                z_score = anomaly_result.get('z_score', 0)
                fraud_analysis['fraud_score'] += min(z_score * 20, 80)  # Cap at 80 points
                logger.warning(f"Transaction {transaction_id} flagged: statistical anomaly (Z-score: {z_score})")
                
        except Exception as e:
            logger.error(f"Error in statistical anomaly detection: {e}")
            fraud_analysis['details']['statistical_anomaly'] = {'error': str(e)}
        
        # Step 3: Geographical drift detection
        try:
            if latitude is not None and longitude is not None:
                drift_result = self.drift_detector.detect_geographical_drift(
                    card_id, latitude, longitude, location_name, historical_transactions
                )
                fraud_analysis['details']['geographical_drift'] = drift_result
                
                if drift_result.get('is_drift', False):
                    fraud_analysis['is_fraudulent'] = True
                    fraud_analysis['fraud_types'].append('geographical_drift')
                    # Score based on distance (further = higher fraud score)
                    distance = drift_result.get('distance_km', 0)
                    fraud_analysis['fraud_score'] += min(distance / 10, 60)  # Cap at 60 points
                    logger.warning(f"Transaction {transaction_id} flagged: geographical drift "
                                 f"({distance}km from last known location)")
                    
                    # Update trusted location after drift detection
                    location_update = self.drift_detector.update_trusted_location(
                        card_id, latitude, longitude, location_name, 
                        transaction_id, transaction.get('timestamp', datetime.now().isoformat())
                    )
                    
                    # Save updated location to database
                    self.db_manager.update_card_location(location_update)
                    
            else:
                fraud_analysis['details']['geographical_drift'] = {
                    'error': 'Location data not available'
                }
                
        except Exception as e:
            logger.error(f"Error in geographical drift detection: {e}")
            fraud_analysis['details']['geographical_drift'] = {'error': str(e)}
        
        # Step 4: Handle fraudulent transactions
        if fraud_analysis['is_fraudulent']:
            self._handle_fraudulent_transaction(transaction, fraud_analysis)
        
        # Step 5: Save transaction and analysis results
        try:
            # Save transaction to database
            self.db_manager.save_transaction(transaction)
            
            # Save fraud alert if fraudulent
            if fraud_analysis['is_fraudulent']:
                alert_data = {
                    'transaction_id': transaction_id,
                    'card_id': card_id,
                    'fraud_type': ', '.join(fraud_analysis['fraud_types']),
                    'severity': self._calculate_severity(fraud_analysis['fraud_score']),
                    'details': fraud_analysis['details'],
                    'status': 'active'
                }
                self.db_manager.save_fraud_alert(alert_data)
                
        except Exception as e:
            logger.error(f"Error saving transaction analysis: {e}")
            fraud_analysis['save_error'] = str(e)
        
        # Round fraud score
        fraud_analysis['fraud_score'] = round(fraud_analysis['fraud_score'], 2)
        
        logger.info(f"Transaction {transaction_id} analysis complete. "
                   f"Fraudulent: {fraud_analysis['is_fraudulent']}, "
                   f"Score: {fraud_analysis['fraud_score']}")
        
        return fraud_analysis
    
    def _handle_fraudulent_transaction(self, transaction: Dict, fraud_analysis: Dict):
        """
        Handle a fraudulent transaction by adding recipient to blacklist if needed.
        
        Args:
            transaction: Original transaction data
            fraud_analysis: Fraud analysis results
        """
        try:
            # Auto-blacklist recipient account if not already blacklisted
            recipient_account = transaction.get('recipient_account')
            
            if recipient_account and 'blacklisted_recipient' not in fraud_analysis['fraud_types']:
                # Determine primary fraud type for blacklist reason
                primary_fraud_type = fraud_analysis['fraud_types'][0] if fraud_analysis['fraud_types'] else 'unknown'
                
                reason = f"Automatically blacklisted due to {primary_fraud_type} fraud detection"
                
                blacklist_result = self.blacklist_manager.add_to_blacklist(
                    recipient_account=recipient_account,
                    reason=reason,
                    fraud_type=primary_fraud_type,
                    transaction_id=transaction.get('transaction_id'),
                    card_id=transaction.get('card_id'),
                    amount=transaction.get('amount'),
                    additional_info=fraud_analysis['details']
                )
                
                fraud_analysis['blacklist_action'] = blacklist_result
                
                if blacklist_result.get('success'):
                    logger.warning(f"Recipient account {recipient_account} added to blacklist")
                else:
                    logger.error(f"Failed to add recipient account {recipient_account} to blacklist: "
                               f"{blacklist_result.get('error')}")
                               
        except Exception as e:
            logger.error(f"Error handling fraudulent transaction: {e}")
            fraud_analysis['blacklist_error'] = str(e)
    
    def _calculate_severity(self, fraud_score: float) -> str:
        """
        Calculate fraud severity based on fraud score.
        
        Args:
            fraud_score: Calculated fraud score
            
        Returns:
            Severity level string
        """
        if fraud_score >= 80:
            return 'high'
        elif fraud_score >= 40:
            return 'medium'
        else:
            return 'low'
    
    def get_service_status(self) -> Dict:
        """
        Get the current status of the fraud detection service.
        
        Returns:
            Dictionary with service status information
        """
        try:
            status = {
                'service_name': 'Fraud Detection Service',
                'is_connected': self.is_connected,
                'configuration': self.config,
                'components': {
                    'statistical_anomaly_detector': {
                        'z_score_threshold': self.config['z_score_threshold'],
                        'lookback_days': self.config['lookback_days']
                    },
                    'geographical_drift_detector': {
                        'distance_threshold_km': self.config['distance_threshold_km']
                    },
                    'auto_blacklist_manager': {
                        'database_name': self.config['database_name']
                    }
                },
                'last_updated': datetime.now().isoformat()
            }
            
            if self.is_connected:
                # Get database statistics
                db_stats = self.db_manager.get_database_stats()
                status['database_stats'] = db_stats
                
                # Get blacklist summary
                blacklist_summary = self.blacklist_manager.get_blacklist_summary()
                status['blacklist_summary'] = blacklist_summary
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                'service_name': 'Fraud Detection Service',
                'error': str(e),
                'is_connected': self.is_connected
            }
    
    def batch_analyze_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """
        Analyze multiple transactions in batch.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of fraud analysis results
        """
        results = []
        
        for transaction in transactions:
            try:
                analysis = self.analyze_transaction(transaction)
                results.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing transaction {transaction.get('transaction_id')}: {e}")
                results.append({
                    'transaction_id': transaction.get('transaction_id'),
                    'error': str(e)
                })
        
        logger.info(f"Batch analysis complete. Processed {len(transactions)} transactions")
        return results