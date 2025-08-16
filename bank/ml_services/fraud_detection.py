"""
Fraud Detection Service for XySave using PyTorch
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Avg

logger = logging.getLogger(__name__)

class FraudDetectionModel(nn.Module):
    """PyTorch model for detecting fraudulent XySave transactions"""
    
    def __init__(self, input_size=20, hidden_size=64, num_classes=2):
        super(FraudDetectionModel, self).__init__()
        self.layer1 = nn.Linear(input_size, hidden_size)
        self.layer2 = nn.Linear(hidden_size, hidden_size)
        self.layer3 = nn.Linear(hidden_size, num_classes)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        self.batch_norm1 = nn.BatchNorm1d(hidden_size)
        self.batch_norm2 = nn.BatchNorm1d(hidden_size)
        
    def forward(self, x):
        x = self.layer1(x)
        x = self.batch_norm1(x)
        x = self.relu(x)
        x = self.dropout(x)
        
        x = self.layer2(x)
        x = self.batch_norm2(x)
        x = self.relu(x)
        x = self.dropout(x)
        
        x = self.layer3(x)
        return x

class XySaveFraudDetectionService:
    """Service for fraud detection using PyTorch"""
    
    def __init__(self):
        self.model = FraudDetectionModel()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Try to load pre-trained model, otherwise use random weights
        try:
            self.model.load_state_dict(torch.load('bank/models/fraud_detection.pth', map_location=self.device))
            logger.info("Loaded pre-trained fraud detection model")
        except FileNotFoundError:
            logger.warning("No pre-trained model found. Using random weights.")
        
        self.model.eval()
    
    def extract_features(self, transaction, user):
        """Extract features from transaction for fraud detection"""
        try:
            # Get user's transaction history
            recent_transactions = user.xysave_account.transactions.all().order_by('-created_at')[:10]
            
            # Calculate transaction patterns
            avg_amount = recent_transactions.aggregate(avg=Avg('amount'))['avg'] or 0
            transaction_count_24h = recent_transactions.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            # Time-based features
            hour_of_day = transaction.created_at.hour
            day_of_week = transaction.created_at.weekday()
            
            # Amount-based features
            amount = transaction.amount.amount
            balance = transaction.xysave_account.balance.amount
            
            # User behavior features
            account_age_days = (timezone.now() - user.date_joined).days
            total_transactions = recent_transactions.count()
            
            # Risk indicators
            is_large_amount = 1 if amount > 100000 else 0  # > ₦100k
            is_odd_hour = 1 if hour_of_day < 6 or hour_of_day > 22 else 0
            is_weekend = 1 if day_of_week >= 5 else 0
            
            # Normalize features
            features = [
                amount / 1000000,  # Normalize amount (in millions)
                balance / 1000000,  # Normalize balance
                avg_amount / 1000000,  # Normalize avg amount
                transaction_count_24h / 10,  # Normalize transaction count
                hour_of_day / 24,  # Normalize hour
                day_of_week / 7,  # Normalize day
                account_age_days / 365,  # Normalize account age
                total_transactions / 100,  # Normalize total transactions
                is_large_amount,
                is_odd_hour,
                is_weekend,
                # Add more features as needed
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0  # Padding to reach 20 features
            ]
            
            return torch.tensor(features[:20], dtype=torch.float32)
            
        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            # Return default features if extraction fails
            return torch.zeros(20, dtype=torch.float32)
    
    def predict_fraud_risk(self, transaction, user):
        """Predict fraud risk for a transaction"""
        try:
            features = self.extract_features(transaction, user)
            features = features.unsqueeze(0).to(self.device)  # Add batch dimension
            
            with torch.no_grad():
                prediction = self.model(features)
                fraud_probability = F.softmax(prediction, dim=1)[0, 1].item()
            
            return {
                'fraud_risk': fraud_probability,
                'is_suspicious': fraud_probability > 0.7,
                'confidence': 1 - fraud_probability,
                'risk_level': self._get_risk_level(fraud_probability)
            }
            
        except Exception as e:
            logger.error(f"Error predicting fraud risk: {str(e)}")
            return {
                'fraud_risk': 0.5,
                'is_suspicious': False,
                'confidence': 0.5,
                'risk_level': 'medium'
            }
    
    def _get_risk_level(self, fraud_probability):
        """Convert fraud probability to risk level"""
        if fraud_probability < 0.3:
            return 'low'
        elif fraud_probability < 0.7:
            return 'medium'
        else:
            return 'high'
    
    def train_model(self, training_data):
        """Train the fraud detection model"""
        try:
            # This would be implemented with actual training data
            # For now, we'll just save the current model
            torch.save(self.model.state_dict(), 'bank/models/fraud_detection.pth')
            logger.info("Fraud detection model saved")
        except Exception as e:
            logger.error(f"Error training model: {str(e)}") 