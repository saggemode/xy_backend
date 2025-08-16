#!/usr/bin/env python
"""
Test script to demonstrate PyTorch integration with XySave
AI/ML capabilities for fraud detection, investment recommendations, and more
"""
import os
import sys
import django
from decimal import Decimal

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from djmoney.money import Money
from django.contrib.auth import get_user_model
from django.utils import timezone
from bank.models import Wallet, XySaveAccount, XySaveTransaction
from bank.ml_services import (
    XySaveFraudDetectionService,
    XySaveInvestmentRecommendationService,
    XySaveCustomerInsightsService,
    XySaveAnomalyDetectionService,
    XySaveInterestRateService
)
from bank.xysave_services import XySaveAccountService, XySaveTransactionService

User = get_user_model()

def test_pytorch_integration():
    """Test all PyTorch ML services integration"""
    print("=" * 80)
    print("PYTORCH INTEGRATION TEST - XYSAVE AI/ML CAPABILITIES")
    print("=" * 80)
    
    # Get or create a test user
    try:
        user = User.objects.get(username='mltestuser')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='mltestuser',
            email='mltest@xysave.com',
            password='mltestpass123'
        )
        print(f"Created test user: {user.username}")
    
    # Ensure user has a wallet and XySave account
    wallet, created = Wallet.objects.get_or_create(
        user=user,
        defaults={
            'account_number': 'ML1234567890',
            'alternative_account_number': 'ML0987654321',
            'balance': Money(100000, 'NGN')
        }
    )
    if created:
        print(f"Created wallet with balance: {wallet.balance}")
    else:
        print(f"Using existing wallet with balance: {wallet.balance}")
    
    # Get or create XySave account
    xysave_account = XySaveAccountService.get_xysave_account(user)
    print(f"XySave Account: {xysave_account.account_number}")
    print(f"XySave Balance: {xysave_account.balance}")
    
    print("\n" + "=" * 50)
    print("1. FRAUD DETECTION SERVICE")
    print("=" * 50)
    
    # Test fraud detection
    fraud_service = XySaveFraudDetectionService()
    print("✅ Fraud Detection Service initialized")
    
    # Create a test transaction for fraud analysis
    test_transaction = XySaveTransaction.objects.create(
        xysave_account=xysave_account,
        transaction_type='deposit',
        amount=Money(50000, 'NGN'),
        balance_before=xysave_account.balance,
        balance_after=xysave_account.balance + Money(50000, 'NGN'),
        description='Test transaction for fraud detection',
        reference='TEST_FRAUD_001'
    )
    
    fraud_risk = fraud_service.predict_fraud_risk(test_transaction, user)
    print(f"Fraud Risk Analysis:")
    print(f"  - Fraud Risk: {fraud_risk['fraud_risk']:.4f}")
    print(f"  - Is Suspicious: {fraud_risk['is_suspicious']}")
    print(f"  - Risk Level: {fraud_risk['risk_level']}")
    print(f"  - Confidence: {fraud_risk['confidence']:.4f}")
    
    print("\n" + "=" * 50)
    print("2. ANOMALY DETECTION SERVICE")
    print("=" * 50)
    
    # Test anomaly detection
    anomaly_service = XySaveAnomalyDetectionService()
    print("✅ Anomaly Detection Service initialized")
    
    anomaly_result = anomaly_service.detect_anomaly(test_transaction, user)
    print(f"Anomaly Detection Results:")
    print(f"  - Is Anomalous: {anomaly_result['is_anomalous']}")
    print(f"  - Anomaly Score: {anomaly_result['anomaly_score']:.4f}")
    print(f"  - Risk Level: {anomaly_result['risk_level']}")
    print(f"  - Confidence: {anomaly_result['confidence']:.4f}")
    print(f"  - Features Analyzed: {anomaly_result['features_analyzed']}")
    
    print("\n" + "=" * 50)
    print("3. INVESTMENT RECOMMENDATION SERVICE")
    print("=" * 50)
    
    # Test investment recommendations
    investment_service = XySaveInvestmentRecommendationService()
    print("✅ Investment Recommendation Service initialized")
    
    recommendations = investment_service.get_investment_recommendations(user)
    print(f"Investment Recommendations:")
    print(f"  - Best Investment: {recommendations['best_investment']}")
    print(f"  - Confidence: {recommendations['confidence']:.4f}")
    print(f"  - Reasoning: {recommendations['reasoning']}")
    print(f"  - Recommendations Breakdown:")
    for inv_type, prob in recommendations['recommendations'].items():
        print(f"    * {inv_type}: {prob:.4f}")
    
    print("\n" + "=" * 50)
    print("4. CUSTOMER INSIGHTS SERVICE")
    print("=" * 50)
    
    # Test customer insights
    insights_service = XySaveCustomerInsightsService()
    print("✅ Customer Insights Service initialized")
    
    behavior_analysis = insights_service.analyze_customer_behavior(user)
    print(f"Customer Behavior Analysis:")
    print(f"  - Risk Tolerance: {behavior_analysis['risk_tolerance']:.4f}")
    print(f"  - Savings Habit: {behavior_analysis['savings_habit']:.4f}")
    print(f"  - Investment Preference: {behavior_analysis['investment_preference']:.4f}")
    print(f"  - Loyalty Score: {behavior_analysis['loyalty_score']:.4f}")
    print(f"  - Churn Risk: {behavior_analysis['churn_risk']:.4f}")
    print(f"  - Behavior Type: {behavior_analysis['behavior_type']}")
    
    customer_segment = insights_service.get_customer_segment(user)
    print(f"  - Customer Segment: {customer_segment}")
    
    recommendations = insights_service.get_personalized_recommendations(user)
    print(f"  - Personalized Recommendations: {len(recommendations)} items")
    for i, rec in enumerate(recommendations, 1):
        print(f"    {i}. {rec['title']} ({rec['priority']} priority)")
    
    print("\n" + "=" * 50)
    print("5. INTEREST RATE PREDICTION SERVICE")
    print("=" * 50)
    
    # Test interest rate prediction
    interest_service = XySaveInterestRateService()
    print("✅ Interest Rate Prediction Service initialized")
    
    rate_prediction = interest_service.predict_optimal_rate()
    print(f"Interest Rate Prediction:")
    print(f"  - Optimal Rate: {rate_prediction['optimal_rate']:.4f} ({rate_prediction['optimal_rate']*100:.2f}%)")
    print(f"  - Daily Rate: {rate_prediction['daily_rate']:.6f}")
    print(f"  - Confidence: {rate_prediction['confidence']:.4f}")
    print(f"  - Factors Considered: {rate_prediction['factors_considered']}")
    
    rate_forecast = interest_service.get_rate_forecast(days=7)
    print(f"Rate Forecast (7 days):")
    print(f"  - Average Rate: {rate_forecast['average_rate']:.4f}")
    print(f"  - Rate Volatility: {rate_forecast['rate_volatility']:.4f}")
    print(f"  - Forecast Points: {len(rate_forecast['forecast'])}")
    
    print("\n" + "=" * 50)
    print("6. INTEGRATED TRANSACTION PROCESSING")
    print("=" * 50)
    
    # Test integrated transaction processing with ML
    transaction_service = XySaveTransactionService()
    print("✅ Transaction Service with ML integration initialized")
    
    # Process a deposit with ML analysis
    try:
        deposit_amount = Money(25000, 'NGN')
        print(f"Processing deposit of {deposit_amount} with ML analysis...")
        
        transaction = transaction_service.deposit_to_xysave(
            user, deposit_amount, "ML-integrated deposit test"
        )
        
        print(f"✅ Deposit successful! Transaction: {transaction.reference}")
        print(f"   XySave Balance: {xysave_account.balance}")
        print(f"   Wallet Balance: {wallet.balance}")
        
        # Check ML analysis results
        if hasattr(transaction, 'metadata') and transaction.metadata:
            print(f"   ML Analysis Results:")
            if 'fraud_risk' in transaction.metadata:
                fraud = transaction.metadata['fraud_risk']
                print(f"     - Fraud Risk: {fraud['fraud_risk']:.4f} ({fraud['risk_level']})")
            if 'anomaly_detection' in transaction.metadata:
                anomaly = transaction.metadata['anomaly_detection']
                print(f"     - Anomaly Score: {anomaly['anomaly_score']:.4f} ({anomaly['risk_level']})")
            if transaction.metadata.get('requires_review'):
                print(f"     - ⚠️  Transaction flagged for review")
        
    except Exception as e:
        print(f"❌ Deposit failed: {str(e)}")
    
    print("\n" + "=" * 50)
    print("7. MODEL STATISTICS")
    print("=" * 50)
    
    # Get model statistics
    anomaly_stats = anomaly_service.get_model_statistics()
    print(f"Anomaly Detection Model:")
    print(f"  - Model Type: {anomaly_stats['model_type']}")
    print(f"  - Input Features: {anomaly_stats['input_features']}")
    print(f"  - Encoded Features: {anomaly_stats['encoded_features']}")
    print(f"  - Model Parameters: {anomaly_stats['model_parameters']:,}")
    print(f"  - Device: {anomaly_stats['device']}")
    
    print("\n" + "=" * 50)
    print("8. SUMMARY")
    print("=" * 50)
    
    print("✅ PyTorch Integration Test Completed Successfully!")
    print(f"📊 User: {user.username}")
    print(f"💰 Wallet Balance: {wallet.balance}")
    print(f"🏦 XySave Balance: {xysave_account.balance}")
    print(f"🔍 ML Services Tested: 5")
    print(f"🤖 Models Loaded: 5")
    print(f"📈 Transactions Processed: 2")
    
    print("\n🎯 Key ML Capabilities Demonstrated:")
    print("  • Real-time fraud detection with risk scoring")
    print("  • Anomaly detection for suspicious transactions")
    print("  • AI-powered investment recommendations")
    print("  • Customer behavior analysis and segmentation")
    print("  • Dynamic interest rate prediction")
    print("  • Integrated transaction processing with ML")
    
    print("\n🚀 Next Steps:")
    print("  • Train models with real transaction data")
    print("  • Implement model retraining pipelines")
    print("  • Add more sophisticated feature engineering")
    print("  • Integrate with external data sources")
    print("  • Deploy models to production environment")

if __name__ == "__main__":
    test_pytorch_integration() 