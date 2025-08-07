import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class StatisticalAnomalyDetector:
    """
    Detects anomalous transaction amounts using Z-score analysis.
    Flags transactions with Z-score > 2.5 as abnormal spikes.
    """
    
    def __init__(self, z_score_threshold: float = 2.5, lookback_days: int = 30):
        self.z_score_threshold = z_score_threshold
        self.lookback_days = lookback_days
    
    def calculate_z_score(self, amount: float, historical_amounts: List[float]) -> float:
        """
        Calculate Z-score for a transaction amount against historical data.
        
        Args:
            amount: Current transaction amount
            historical_amounts: List of historical transaction amounts
            
        Returns:
            Z-score value
        """
        if len(historical_amounts) < 2:
            logger.warning("Insufficient historical data for Z-score calculation")
            return 0.0
        
        historical_array = np.array(historical_amounts)
        mean = np.mean(historical_array)
        std_dev = np.std(historical_array)
        
        # Avoid division by zero
        if std_dev == 0:
            return 0.0 if amount == mean else float('inf')
        
        z_score = (amount - mean) / std_dev
        return abs(z_score)
    
    def is_anomalous_transaction(self, 
                               card_id: str, 
                               amount: float, 
                               historical_transactions: List[Dict]) -> Dict:
        """
        Check if a transaction amount is anomalous based on historical patterns.
        
        Args:
            card_id: Card identifier
            amount: Transaction amount to check
            historical_transactions: List of historical transaction dictionaries
            
        Returns:
            Dictionary with anomaly detection results
        """
        # Filter transactions for the specific card within lookback period
        cutoff_date = datetime.now() - timedelta(days=self.lookback_days)
        
        card_transactions = [
            t for t in historical_transactions 
            if t.get('card_id') == card_id and 
            datetime.fromisoformat(t.get('timestamp', '1900-01-01')) >= cutoff_date
        ]
        
        if len(card_transactions) < 2:
            logger.info(f"Insufficient historical data for card {card_id}")
            return {
                'is_anomalous': False,
                'z_score': 0.0,
                'reason': 'Insufficient historical data',
                'threshold': self.z_score_threshold,
                'historical_count': len(card_transactions)
            }
        
        # Extract amounts from historical transactions
        historical_amounts = [t.get('amount', 0.0) for t in card_transactions]
        
        # Calculate Z-score
        z_score = self.calculate_z_score(amount, historical_amounts)
        
        # Check if anomalous
        is_anomalous = z_score > self.z_score_threshold
        
        result = {
            'is_anomalous': is_anomalous,
            'z_score': round(z_score, 3),
            'threshold': self.z_score_threshold,
            'historical_count': len(card_transactions),
            'historical_mean': round(np.mean(historical_amounts), 2),
            'historical_std': round(np.std(historical_amounts), 2),
            'reason': f'Z-score {z_score:.3f} > threshold {self.z_score_threshold}' if is_anomalous else 'Normal transaction pattern'
        }
        
        if is_anomalous:
            logger.warning(f"Anomalous transaction detected for card {card_id}: "
                         f"Amount {amount}, Z-score {z_score:.3f}")
        
        return result
    
    def get_transaction_statistics(self, card_id: str, historical_transactions: List[Dict]) -> Dict:
        """
        Get statistical summary for a card's transaction history.
        
        Args:
            card_id: Card identifier
            historical_transactions: List of historical transaction dictionaries
            
        Returns:
            Statistical summary dictionary
        """
        cutoff_date = datetime.now() - timedelta(days=self.lookback_days)
        
        card_transactions = [
            t for t in historical_transactions 
            if t.get('card_id') == card_id and 
            datetime.fromisoformat(t.get('timestamp', '1900-01-01')) >= cutoff_date
        ]
        
        if not card_transactions:
            return {'error': 'No historical transactions found'}
        
        amounts = [t.get('amount', 0.0) for t in card_transactions]
        amounts_array = np.array(amounts)
        
        return {
            'card_id': card_id,
            'transaction_count': len(amounts),
            'mean_amount': round(np.mean(amounts_array), 2),
            'std_dev': round(np.std(amounts_array), 2),
            'min_amount': round(np.min(amounts_array), 2),
            'max_amount': round(np.max(amounts_array), 2),
            'median_amount': round(np.median(amounts_array), 2),
            'lookback_days': self.lookback_days
        }