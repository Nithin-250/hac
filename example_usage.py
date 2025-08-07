#!/usr/bin/env python3
"""
Example usage of the Fraud Detection System

This script demonstrates how to use the fraud detection system to analyze transactions
for statistical anomalies, geographical drift, and automatic blacklisting.
"""

import logging
from datetime import datetime, timedelta
from fraud_detection_service import FraudDetectionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_sample_transactions():
    """Create sample transactions for demonstration."""
    base_time = datetime.now()
    
    # Sample transactions with various patterns
    transactions = [
        {
            'transaction_id': 'TXN001',
            'card_id': 'CARD_12345',
            'amount': 150.00,
            'recipient_account': 'ACC_NORMAL_001',
            'latitude': 13.0827,  # Chennai
            'longitude': 80.2707,
            'location_name': 'Chennai',
            'timestamp': (base_time - timedelta(days=5)).isoformat(),
            'merchant_id': 'MERCHANT_001'
        },
        {
            'transaction_id': 'TXN002',
            'card_id': 'CARD_12345',
            'amount': 200.00,
            'recipient_account': 'ACC_NORMAL_002',
            'latitude': 13.0827,  # Chennai
            'longitude': 80.2707,
            'location_name': 'Chennai',
            'timestamp': (base_time - timedelta(days=4)).isoformat(),
            'merchant_id': 'MERCHANT_002'
        },
        {
            'transaction_id': 'TXN003',
            'card_id': 'CARD_12345',
            'amount': 175.50,
            'recipient_account': 'ACC_NORMAL_003',
            'latitude': 13.0827,  # Chennai
            'longitude': 80.2707,
            'location_name': 'Chennai',
            'timestamp': (base_time - timedelta(days=3)).isoformat(),
            'merchant_id': 'MERCHANT_003'
        },
        # Anomalous amount transaction (should trigger statistical anomaly)
        {
            'transaction_id': 'TXN004',
            'card_id': 'CARD_12345',
            'amount': 5000.00,  # Much higher than normal
            'recipient_account': 'ACC_SUSPICIOUS_001',
            'latitude': 13.0827,  # Chennai
            'longitude': 80.2707,
            'location_name': 'Chennai',
            'timestamp': (base_time - timedelta(days=1)).isoformat(),
            'merchant_id': 'MERCHANT_004'
        },
        # Geographical drift transaction (should trigger location drift)
        {
            'transaction_id': 'TXN005',
            'card_id': 'CARD_12345',
            'amount': 300.00,
            'recipient_account': 'ACC_DISTANT_001',
            'latitude': 28.7041,  # Delhi (far from Chennai)
            'longitude': 77.1025,
            'location_name': 'Delhi',
            'timestamp': base_time.isoformat(),
            'merchant_id': 'MERCHANT_005'
        },
        # Transaction to previously blacklisted account
        {
            'transaction_id': 'TXN006',
            'card_id': 'CARD_67890',
            'amount': 100.00,
            'recipient_account': 'ACC_SUSPICIOUS_001',  # Same as TXN004 (will be blacklisted)
            'latitude': 19.0760,  # Mumbai
            'longitude': 72.8777,
            'location_name': 'Mumbai',
            'timestamp': (base_time + timedelta(minutes=30)).isoformat(),
            'merchant_id': 'MERCHANT_006'
        }
    ]
    
    return transactions

def main():
    """Main demonstration function."""
    print("🔍 Fraud Detection System Demo")
    print("=" * 50)
    
    # Initialize fraud detection service
    fraud_service = FraudDetectionService(
        mongo_uri="mongodb://localhost:27017/",
        database_name="fraud_detection_demo",
        z_score_threshold=2.5,
        distance_threshold_km=500.0,
        lookback_days=30
    )
    
    # Connect to services
    print("\n📡 Connecting to services...")
    if not fraud_service.connect():
        print("❌ Failed to connect to fraud detection service")
        return
    
    print("✅ Successfully connected to fraud detection service")
    
    try:
        # Get service status
        print("\n📊 Service Status:")
        status = fraud_service.get_service_status()
        print(f"   Service: {status['service_name']}")
        print(f"   Connected: {status['is_connected']}")
        print(f"   Z-score Threshold: {status['configuration']['z_score_threshold']}")
        print(f"   Distance Threshold: {status['configuration']['distance_threshold_km']} km")
        
        # Create sample transactions
        print("\n📝 Creating sample transactions...")
        transactions = create_sample_transactions()
        print(f"   Created {len(transactions)} sample transactions")
        
        # Analyze transactions
        print("\n🔍 Analyzing transactions for fraud...")
        print("-" * 50)
        
        for i, transaction in enumerate(transactions, 1):
            print(f"\n🔍 Analyzing Transaction {i}/{len(transactions)}")
            print(f"   ID: {transaction['transaction_id']}")
            print(f"   Card: {transaction['card_id']}")
            print(f"   Amount: ${transaction['amount']:.2f}")
            print(f"   Location: {transaction['location_name']}")
            print(f"   Recipient: {transaction['recipient_account']}")
            
            # Analyze transaction
            result = fraud_service.analyze_transaction(transaction)
            
            # Display results
            if result.get('is_fraudulent', False):
                print(f"   🚨 FRAUD DETECTED!")
                print(f"   Fraud Types: {', '.join(result['fraud_types'])}")
                print(f"   Fraud Score: {result['fraud_score']}")
                
                # Show details for each fraud type
                for fraud_type in result['fraud_types']:
                    if fraud_type == 'statistical_anomaly':
                        anomaly_details = result['details'].get('statistical_anomaly', {})
                        z_score = anomaly_details.get('z_score', 0)
                        print(f"   📊 Statistical Anomaly: Z-score = {z_score}")
                    
                    elif fraud_type == 'geographical_drift':
                        drift_details = result['details'].get('geographical_drift', {})
                        distance = drift_details.get('distance_km', 0)
                        last_location = drift_details.get('last_location', 'Unknown')
                        print(f"   📍 Geographical Drift: {distance}km from {last_location}")
                    
                    elif fraud_type == 'blacklisted_recipient':
                        print(f"   🛑 Blacklisted Recipient Account")
                
                # Show blacklist action if taken
                if 'blacklist_action' in result:
                    action = result['blacklist_action']
                    if action.get('success'):
                        print(f"   ✅ Account {transaction['recipient_account']} added to blacklist")
                    else:
                        print(f"   ❌ Failed to blacklist account: {action.get('error')}")
            
            else:
                print(f"   ✅ Transaction appears legitimate")
                print(f"   Fraud Score: {result['fraud_score']}")
        
        # Show final service status with updated statistics
        print("\n📊 Final Service Statistics:")
        print("-" * 30)
        final_status = fraud_service.get_service_status()
        
        if 'database_stats' in final_status:
            db_stats = final_status['database_stats']
            collections = db_stats.get('collections', {})
            
            print(f"   Transactions: {collections.get('transactions', {}).get('document_count', 0)}")
            print(f"   Fraud Alerts: {collections.get('fraud_alerts', {}).get('document_count', 0)}")
            print(f"   Card Locations: {collections.get('card_locations', {}).get('document_count', 0)}")
            print(f"   Blacklisted Accounts: {collections.get('blacklisted_accounts', {}).get('document_count', 0)}")
        
        if 'blacklist_summary' in final_status:
            blacklist_summary = final_status['blacklist_summary']
            print(f"   Active Blacklisted: {blacklist_summary.get('total_active_blacklisted', 0)}")
            
            fraud_types = blacklist_summary.get('fraud_type_distribution', {})
            if fraud_types:
                print("   Fraud Type Distribution:")
                for fraud_type, count in fraud_types.items():
                    print(f"     - {fraud_type}: {count}")
        
        print("\n🎉 Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        
    finally:
        # Disconnect from services
        print("\n📡 Disconnecting from services...")
        fraud_service.disconnect()
        print("✅ Disconnected successfully")

if __name__ == "__main__":
    main()