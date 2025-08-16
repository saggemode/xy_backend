"""
Interest Rate Prediction Service for XySave using PyTorch
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

class InterestRatePredictionModel(nn.Module):
    """PyTorch model for predicting optimal interest rates"""
    
    def __init__(self, sequence_length=30, input_size=10, hidden_size=128, num_layers=2):
        super(InterestRatePredictionModel, self).__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2
        )
        self.fc1 = nn.Linear(hidden_size, hidden_size // 2)
        self.fc2 = nn.Linear(hidden_size // 2, 1)
        self.dropout = nn.Dropout(0.3)
        self.batch_norm = nn.BatchNorm1d(hidden_size // 2)
        
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last_output = lstm_out[:, -1, :]  # Take the last output
        x = self.fc1(last_output)
        x = self.batch_norm(x)
        x = F.relu(x)
        x = self.dropout(x)
        prediction = self.fc2(x)
        return torch.sigmoid(prediction)  # Output between 0 and 1

class XySaveInterestRateService:
    """Service for dynamic interest rate adjustment using PyTorch"""
    
    def __init__(self):
        self.model = InterestRatePredictionModel()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Try to load pre-trained model, otherwise use random weights
        try:
            self.model.load_state_dict(torch.load('bank/pytorch_models/interest_rate_prediction.pth', map_location=self.device))
            logger.info("Loaded pre-trained interest rate prediction model")
        except FileNotFoundError:
            logger.warning("No pre-trained model found. Using random weights.")
        
        self.model.eval()
        
        # Economic indicators mapping
        self.economic_indicators = [
            'treasury_bill_rate',
            'inflation_rate',
            'gdp_growth',
            'exchange_rate_stability',
            'interest_rate_environment',
            'market_volatility',
            'banking_sector_health',
            'regulatory_environment',
            'economic_outlook',
            'competition_level'
        ]
    
    def get_economic_indicators(self):
        """Get current economic indicators (simulated for now)"""
        try:
            # In a real implementation, this would fetch live economic data
            # For now, we'll simulate realistic Nigerian economic conditions
            
            # Simulate economic indicators based on current market conditions
            base_date = timezone.now()
            
            # Treasury bill rates (CBN data)
            treasury_bill_rate = 0.12  # 12% p.a.
            
            # Inflation rate (NBS data)
            inflation_rate = 0.18  # 18% inflation
            
            # GDP growth
            gdp_growth = 0.03  # 3% GDP growth
            
            # Exchange rate stability (NGN/USD)
            exchange_rate_stability = 0.8  # 80% stable
            
            # Interest rate environment
            interest_rate_environment = 0.14  # 14% base rate
            
            # Market volatility
            market_volatility = 0.15  # 15% volatility
            
            # Banking sector health
            banking_sector_health = 0.85  # 85% healthy
            
            # Regulatory environment
            regulatory_environment = 0.9  # 90% favorable
            
            # Economic outlook
            economic_outlook = 0.75  # 75% positive
            
            # Competition level in fintech
            competition_level = 0.7  # 70% competitive
            
            indicators = [
                treasury_bill_rate,
                inflation_rate,
                gdp_growth,
                exchange_rate_stability,
                interest_rate_environment,
                market_volatility,
                banking_sector_health,
                regulatory_environment,
                economic_outlook,
                competition_level
            ]
            
            return torch.tensor(indicators, dtype=torch.float32)
            
        except Exception as e:
            logger.error(f"Error getting economic indicators: {str(e)}")
            return torch.zeros(10, dtype=torch.float32)
    
    def get_historical_economic_data(self, days=30):
        """Get historical economic data for sequence prediction"""
        try:
            # Simulate historical data with some variation
            base_indicators = self.get_economic_indicators()
            historical_data = []
            
            for day in range(days):
                # Add some random variation to simulate historical changes
                variation = torch.randn(10) * 0.02  # 2% variation
                day_indicators = base_indicators + variation
                day_indicators = torch.clamp(day_indicators, 0, 1)  # Keep in valid range
                historical_data.append(day_indicators)
            
            return torch.stack(historical_data)
            
        except Exception as e:
            logger.error(f"Error getting historical economic data: {str(e)}")
            return torch.zeros(30, 10, dtype=torch.float32)
    
    def predict_optimal_rate(self, economic_data=None):
        """Predict optimal interest rate based on economic conditions"""
        try:
            if economic_data is None:
                economic_data = self.get_historical_economic_data()
            
            # Add batch dimension
            economic_data = economic_data.unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                prediction = self.model(economic_data)
                optimal_rate = prediction.item() * 0.25  # Scale to max 25%
            
            return {
                'optimal_rate': optimal_rate,
                'daily_rate': optimal_rate / 365,
                'confidence': 0.85,  # Simulated confidence
                'factors_considered': len(self.economic_indicators),
                'prediction_timestamp': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error predicting optimal rate: {str(e)}")
            return {
                'optimal_rate': 0.15,  # Default 15%
                'daily_rate': 0.15 / 365,
                'confidence': 0.5,
                'factors_considered': 0,
                'prediction_timestamp': timezone.now()
            }
    
    def adjust_interest_rates(self):
        """Dynamically adjust interest rates based on predictions"""
        try:
            from bank.models import XySaveAccount
            
            # Get optimal rate prediction
            rate_prediction = self.predict_optimal_rate()
            optimal_daily_rate = rate_prediction['daily_rate']
            
            # Update all active accounts
            active_accounts = XySaveAccount.objects.filter(is_active=True)
            updated_count = 0
            
            for account in active_accounts:
                old_rate = account.daily_interest_rate
                account.daily_interest_rate = optimal_daily_rate
                account.save()
                updated_count += 1
                
                logger.info(f"Updated interest rate for account {account.account_number}: "
                          f"{old_rate:.6f} -> {optimal_daily_rate:.6f}")
            
            return {
                'accounts_updated': updated_count,
                'new_daily_rate': optimal_daily_rate,
                'new_annual_rate': optimal_daily_rate * 365,
                'prediction_confidence': rate_prediction['confidence'],
                'adjustment_timestamp': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error adjusting interest rates: {str(e)}")
            return {
                'accounts_updated': 0,
                'error': str(e),
                'adjustment_timestamp': timezone.now()
            }
    
    def get_rate_forecast(self, days=30):
        """Get interest rate forecast for the next N days"""
        try:
            forecast = []
            current_data = self.get_historical_economic_data()
            
            for day in range(days):
                # Predict rate for this day
                day_prediction = self.predict_optimal_rate(current_data)
                forecast.append({
                    'day': day + 1,
                    'date': timezone.now() + timedelta(days=day),
                    'predicted_rate': day_prediction['optimal_rate'],
                    'confidence': day_prediction['confidence']
                })
                
                # Update economic data for next day (simulate progression)
                variation = torch.randn(10) * 0.01  # 1% daily variation
                current_data = current_data + variation.unsqueeze(0)
                current_data = torch.clamp(current_data, 0, 1)
            
            return {
                'forecast': forecast,
                'average_rate': np.mean([f['predicted_rate'] for f in forecast]),
                'rate_volatility': np.std([f['predicted_rate'] for f in forecast]),
                'forecast_generated': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting rate forecast: {str(e)}")
            return {
                'forecast': [],
                'error': str(e),
                'forecast_generated': timezone.now()
            }
    
    def analyze_rate_impact(self, new_rate):
        """Analyze the impact of a new interest rate on user behavior"""
        try:
            from bank.models import XySaveAccount
            
            # Get current user statistics
            total_accounts = XySaveAccount.objects.filter(is_active=True).count()
            total_balance = XySaveAccount.objects.filter(is_active=True).aggregate(
                total=Sum('balance')
            )['total'] or 0
            
            # Simulate impact analysis
            current_rate = 0.15  # Assume current 15% rate
            rate_change = new_rate - current_rate
            
            # Estimate impact on deposits (simplified model)
            if rate_change > 0:
                deposit_increase = min(rate_change * 2, 0.5)  # Max 50% increase
                withdrawal_decrease = min(rate_change * 1.5, 0.3)  # Max 30% decrease
            else:
                deposit_increase = max(rate_change * 2, -0.3)  # Max 30% decrease
                withdrawal_decrease = max(rate_change * 1.5, -0.2)  # Max 20% increase
            
            return {
                'current_rate': current_rate,
                'proposed_rate': new_rate,
                'rate_change': rate_change,
                'estimated_deposit_change': deposit_increase,
                'estimated_withdrawal_change': withdrawal_decrease,
                'total_accounts_affected': total_accounts,
                'total_balance_affected': total_balance,
                'analysis_timestamp': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing rate impact: {str(e)}")
            return {
                'error': str(e),
                'analysis_timestamp': timezone.now()
            }
    
    def train_model(self, training_data):
        """Train the interest rate prediction model"""
        try:
            # This would be implemented with actual training data
            # For now, we'll just save the current model
            torch.save(self.model.state_dict(), 'bank/pytorch_models/interest_rate_prediction.pth')
            logger.info("Interest rate prediction model saved")
        except Exception as e:
            logger.error(f"Error training model: {str(e)}") 