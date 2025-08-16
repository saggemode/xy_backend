"""
Anomaly Detection Service for XySave using PyTorch
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

class AnomalyDetectionModel(nn.Module):
    """PyTorch autoencoder for transaction anomaly detection"""
    
    def __init__(self, input_size=15):
        super(AnomalyDetectionModel, self).__init__()
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.BatchNorm1d(32),
            nn.Linear(32, 16)
        )
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.BatchNorm1d(32),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Linear(64, input_size)
        )
        
    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded
    
    def encode(self, x):
        """Get encoded representation"""
        return self.encoder(x)

class XySaveAnomalyDetectionService:
    """Service for detecting anomalous transactions using PyTorch"""
    
    def __init__(self):
        self.model = AnomalyDetectionModel()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Try to load pre-trained model, otherwise use random weights
        try:
            self.model.load_state_dict(torch.load('bank/pytorch_models/anomaly_detection.pth', map_location=self.device))
            logger.info("Loaded pre-trained anomaly detection model")
        except FileNotFoundError:
            logger.warning("No pre-trained model found. Using random weights.")
        
        self.model.eval()
        self.threshold = 0.1  # Anomaly threshold
        self.feature_means = None
        self.feature_stds = None
    
    def extract_transaction_features(self, transaction, user):
        """Extract features from transaction for anomaly detection"""
        try:
            account = user.xysave_account
            
            # Transaction features
            amount = transaction.amount.amount
            transaction_type = 1 if transaction.transaction_type == 'deposit' else 0
            
            # Time features
            hour_of_day = transaction.created_at.hour
            day_of_week = transaction.created_at.weekday()
            is_weekend = 1 if day_of_week >= 5 else 0
            is_odd_hour = 1 if hour_of_day < 6 or hour_of_day > 22 else 0
            
            # User behavior features
            recent_transactions = account.transactions.all().order_by('-created_at')[:50]
            avg_amount = recent_transactions.aggregate(avg=Avg('amount'))['avg'] or 0
            transaction_count_24h = recent_transactions.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            # Account features
            balance = account.balance.amount
            account_age_days = (timezone.now() - user.date_joined).days
            
            # Amount-based features
            amount_ratio = amount / max(balance, 1)
            amount_deviation = abs(amount - avg_amount) / max(avg_amount, 1)
            
            # Frequency features
            transactions_per_day = recent_transactions.count() / max(account_age_days, 1)
            
            # Risk indicators
            is_large_amount = 1 if amount > 100000 else 0
            is_suspicious_time = 1 if is_odd_hour and is_weekend else 0
            
            # Normalize features
            features = [
                amount / 1000000,  # Amount in millions
                transaction_type,
                hour_of_day / 24,  # Normalize hour
                day_of_week / 7,  # Normalize day
                is_weekend,
                is_odd_hour,
                avg_amount / 1000000,  # Avg amount in millions
                transaction_count_24h / 10,  # Normalize count
                balance / 1000000,  # Balance in millions
                account_age_days / 365,  # Account age in years
                amount_ratio,
                amount_deviation,
                transactions_per_day / 5,  # Normalize frequency
                is_large_amount,
                is_suspicious_time
            ]
            
            return torch.tensor(features, dtype=torch.float32)
            
        except Exception as e:
            logger.error(f"Error extracting transaction features: {str(e)}")
            return torch.zeros(15, dtype=torch.float32)
    
    def detect_anomaly(self, transaction, user):
        """Detect if a transaction is anomalous"""
        try:
            features = self.extract_transaction_features(transaction, user)
            features = features.unsqueeze(0).to(self.device)  # Add batch dimension
            
            with torch.no_grad():
                reconstructed = self.model(features)
                reconstruction_error = F.mse_loss(features, reconstructed).item()
            
            is_anomalous = reconstruction_error > self.threshold
            
            return {
                'is_anomalous': is_anomalous,
                'anomaly_score': reconstruction_error,
                'confidence': 1 - reconstruction_error,
                'risk_level': self._get_anomaly_risk_level(reconstruction_error),
                'features_analyzed': features.shape[1],
                'threshold': self.threshold
            }
            
        except Exception as e:
            logger.error(f"Error detecting anomaly: {str(e)}")
            return {
                'is_anomalous': False,
                'anomaly_score': 0.0,
                'confidence': 0.5,
                'risk_level': 'low',
                'features_analyzed': 0,
                'threshold': self.threshold
            }
    
    def _get_anomaly_risk_level(self, reconstruction_error):
        """Convert reconstruction error to risk level"""
        if reconstruction_error < 0.05:
            return 'low'
        elif reconstruction_error < 0.1:
            return 'medium'
        else:
            return 'high'
    
    def batch_detect_anomalies(self, transactions, user):
        """Detect anomalies in a batch of transactions"""
        try:
            results = []
            for transaction in transactions:
                anomaly_result = self.detect_anomaly(transaction, user)
                results.append({
                    'transaction_id': transaction.id,
                    'anomaly_result': anomaly_result
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch anomaly detection: {str(e)}")
            return []
    
    def update_threshold(self, new_threshold):
        """Update the anomaly detection threshold"""
        self.threshold = new_threshold
        logger.info(f"Updated anomaly detection threshold to {new_threshold}")
    
    def get_model_statistics(self):
        """Get model statistics and performance metrics"""
        try:
            return {
                'model_type': 'Autoencoder',
                'input_features': 15,
                'encoded_features': 16,
                'threshold': self.threshold,
                'device': str(self.device),
                'model_parameters': sum(p.numel() for p in self.model.parameters()),
                'trainable_parameters': sum(p.numel() for p in self.model.parameters() if p.requires_grad)
            }
        except Exception as e:
            logger.error(f"Error getting model statistics: {str(e)}")
            return {}
    
    def train_model(self, training_data):
        """Train the anomaly detection model"""
        try:
            # This would be implemented with actual training data
            # For now, we'll just save the current model
            torch.save(self.model.state_dict(), 'bank/pytorch_models/anomaly_detection.pth')
            logger.info("Anomaly detection model saved")
        except Exception as e:
            logger.error(f"Error training model: {str(e)}") 