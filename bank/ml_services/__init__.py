"""
XySave ML Services Package
AI/ML capabilities for XySave using PyTorch
"""

from .fraud_detection import XySaveFraudDetectionService
from .investment_recommendations import XySaveInvestmentRecommendationService
from .interest_rate_prediction import XySaveInterestRateService
from .customer_insights import XySaveCustomerInsightsService
from .anomaly_detection import XySaveAnomalyDetectionService

__all__ = [
    'XySaveFraudDetectionService',
    'XySaveInvestmentRecommendationService', 
    'XySaveInterestRateService',
    'XySaveCustomerInsightsService',
    'XySaveAnomalyDetectionService'
] 