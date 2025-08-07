import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class GeographicalDriftDetector:
    """
    Detects geographical anomalies in transactions by calculating distance
    between current and last known location of a card.
    Flags transactions if distance > 500 km.
    """
    
    def __init__(self, distance_threshold_km: float = 500.0):
        self.distance_threshold_km = distance_threshold_km
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth.
        
        Args:
            lat1, lon1: Latitude and longitude of first point
            lat2, lon2: Latitude and longitude of second point
            
        Returns:
            Distance in kilometers
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of Earth in kilometers
        earth_radius_km = 6371.0
        
        return c * earth_radius_km
    
    def get_last_known_location(self, card_id: str, historical_transactions: List[Dict]) -> Optional[Dict]:
        """
        Get the most recent location for a card from historical transactions.
        
        Args:
            card_id: Card identifier
            historical_transactions: List of historical transaction dictionaries
            
        Returns:
            Dictionary with last known location or None if not found
        """
        # Filter transactions for the specific card
        card_transactions = [
            t for t in historical_transactions 
            if t.get('card_id') == card_id and 
            t.get('latitude') is not None and 
            t.get('longitude') is not None
        ]
        
        if not card_transactions:
            return None
        
        # Sort by timestamp to get the most recent transaction
        try:
            sorted_transactions = sorted(
                card_transactions, 
                key=lambda x: datetime.fromisoformat(x.get('timestamp', '1900-01-01')), 
                reverse=True
            )
            
            last_transaction = sorted_transactions[0]
            return {
                'latitude': float(last_transaction['latitude']),
                'longitude': float(last_transaction['longitude']),
                'location_name': last_transaction.get('location_name', 'Unknown'),
                'timestamp': last_transaction.get('timestamp'),
                'transaction_id': last_transaction.get('transaction_id')
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing location data for card {card_id}: {e}")
            return None
    
    def detect_geographical_drift(self, 
                                card_id: str,
                                current_latitude: float,
                                current_longitude: float,
                                current_location_name: str,
                                historical_transactions: List[Dict]) -> Dict:
        """
        Check if current transaction location shows geographical drift.
        
        Args:
            card_id: Card identifier
            current_latitude: Current transaction latitude
            current_longitude: Current transaction longitude
            current_location_name: Current location name (e.g., "Delhi")
            historical_transactions: List of historical transaction dictionaries
            
        Returns:
            Dictionary with drift detection results
        """
        last_location = self.get_last_known_location(card_id, historical_transactions)
        
        if not last_location:
            logger.info(f"No historical location data found for card {card_id}")
            return {
                'is_drift': False,
                'distance_km': 0.0,
                'reason': 'No historical location data available',
                'threshold_km': self.distance_threshold_km,
                'current_location': current_location_name,
                'last_location': 'Unknown'
            }
        
        # Calculate distance between current and last known location
        distance_km = self.haversine_distance(
            last_location['latitude'], last_location['longitude'],
            current_latitude, current_longitude
        )
        
        # Check if distance exceeds threshold
        is_drift = distance_km > self.distance_threshold_km
        
        result = {
            'is_drift': is_drift,
            'distance_km': round(distance_km, 2),
            'threshold_km': self.distance_threshold_km,
            'current_location': current_location_name,
            'last_location': last_location.get('location_name', 'Unknown'),
            'last_transaction_timestamp': last_location.get('timestamp'),
            'reason': f'Distance {distance_km:.2f}km > threshold {self.distance_threshold_km}km' if is_drift else 'Normal geographical pattern'
        }
        
        if is_drift:
            logger.warning(f"Geographical drift detected for card {card_id}: "
                         f"{last_location.get('location_name')} -> {current_location_name}, "
                         f"Distance: {distance_km:.2f}km")
        
        return result
    
    def update_trusted_location(self, 
                              card_id: str, 
                              latitude: float, 
                              longitude: float, 
                              location_name: str,
                              transaction_id: str,
                              timestamp: str) -> Dict:
        """
        Update the trusted location for a card after drift detection.
        Note: This method returns the data that should be saved to update the trusted location.
        The actual database update should be handled by the calling service.
        
        Args:
            card_id: Card identifier
            latitude: New trusted latitude
            longitude: New trusted longitude
            location_name: New trusted location name
            transaction_id: Current transaction ID
            timestamp: Current transaction timestamp
            
        Returns:
            Dictionary with updated location data
        """
        logger.info(f"Updating trusted location for card {card_id} to {location_name}")
        
        return {
            'card_id': card_id,
            'trusted_latitude': latitude,
            'trusted_longitude': longitude,
            'trusted_location_name': location_name,
            'last_update_transaction_id': transaction_id,
            'last_update_timestamp': timestamp,
            'updated_at': datetime.now().isoformat()
        }
    
    def get_location_history(self, card_id: str, historical_transactions: List[Dict]) -> List[Dict]:
        """
        Get location history for a card.
        
        Args:
            card_id: Card identifier
            historical_transactions: List of historical transaction dictionaries
            
        Returns:
            List of location history dictionaries
        """
        card_transactions = [
            t for t in historical_transactions 
            if t.get('card_id') == card_id and 
            t.get('latitude') is not None and 
            t.get('longitude') is not None
        ]
        
        if not card_transactions:
            return []
        
        # Sort by timestamp
        try:
            sorted_transactions = sorted(
                card_transactions, 
                key=lambda x: datetime.fromisoformat(x.get('timestamp', '1900-01-01')), 
                reverse=True
            )
            
            location_history = []
            for transaction in sorted_transactions:
                location_history.append({
                    'latitude': float(transaction['latitude']),
                    'longitude': float(transaction['longitude']),
                    'location_name': transaction.get('location_name', 'Unknown'),
                    'timestamp': transaction.get('timestamp'),
                    'transaction_id': transaction.get('transaction_id')
                })
            
            return location_history
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing location history for card {card_id}: {e}")
            return []