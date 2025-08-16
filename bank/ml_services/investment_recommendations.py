"""
Investment Recommendation Service for XySave using PyTorch
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

class InvestmentRecommendationModel(nn.Module):
    """PyTorch model for investment recommendations"""
    
    def __init__(self, user_features=15, market_features=10, hidden_size=128):
        super(InvestmentRecommendationModel, self).__init__()
        self.user_encoder = nn.Linear(user_features, hidden_size)
        self.market_encoder = nn.Linear(market_features, hidden_size)
        self.recommendation_head = nn.Linear(hidden_size * 2, 4)  # 4 investment types
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
        self.batch_norm1 = nn.BatchNorm1d(hidden_size)
        self.batch_norm2 = nn.BatchNorm1d(hidden_size)
        
    def forward(self, user_features, market_features):
        # Encode user features
        user_encoded = self.user_encoder(user_features)
        user_encoded = self.batch_norm1(user_encoded)
        user_encoded = self.relu(user_encoded)
        user_encoded = self.dropout(user_encoded)
        
        # Encode market features
        market_encoded = self.market_encoder(market_features)
        market_encoded = self.batch_norm2(market_encoded)
        market_encoded = self.relu(market_encoded)
        market_encoded = self.dropout(market_encoded)
        
        # Combine features
        combined = torch.cat([user_encoded, market_encoded], dim=1)
        recommendations = self.recommendation_head(combined)
        return F.softmax(recommendations, dim=1)

class XySaveInvestmentRecommendationService:
    """Service for investment recommendations using PyTorch"""
    
    def __init__(self):
        self.model = InvestmentRecommendationModel()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Try to load pre-trained model, otherwise use random weights
        try:
            self.model.load_state_dict(torch.load('bank/pytorch_models/investment_recommendations.pth', map_location=self.device))
            logger.info("Loaded pre-trained investment recommendation model")
        except FileNotFoundError:
            logger.warning("No pre-trained model found. Using random weights.")
        
        self.model.eval()
        
        # Investment types mapping
        self.investment_types = [
            'treasury_bills',
            'mutual_funds', 
            'government_bonds',
            'short_term_placements'
        ]
    
    def get_user_features(self, user):
        """Extract user features for investment recommendations"""
        try:
            account = user.xysave_account
            
            # Financial features
            balance = account.balance.amount
            total_interest_earned = account.total_interest_earned.amount
            account_age_days = (timezone.now() - user.date_joined).days
            
            # Goal features
            goals = user.xysave_goals.filter(is_active=True)
            total_goals = goals.count()
            avg_goal_amount = goals.aggregate(avg=Avg('target_amount'))['avg'] or 0
            
            # Investment features
            investments = account.investments.filter(is_active=True)
            total_investments = investments.count()
            total_invested = investments.aggregate(total=Sum('amount_invested'))['total'] or 0
            
            # Transaction features
            recent_transactions = account.transactions.all().order_by('-created_at')[:30]
            avg_transaction_amount = recent_transactions.aggregate(avg=Avg('amount'))['avg'] or 0
            transaction_frequency = recent_transactions.count() / 30  # per day
            
            # Risk tolerance indicators
            large_transactions = recent_transactions.filter(amount__gt=50000).count()
            risk_tolerance = large_transactions / max(recent_transactions.count(), 1)
            
            # Normalize features
            features = [
                balance / 1000000,  # Balance in millions
                total_interest_earned / 100000,  # Interest earned in 100k
                account_age_days / 365,  # Account age in years
                total_goals / 10,  # Normalize goals
                avg_goal_amount / 1000000,  # Average goal in millions
                total_investments / 10,  # Normalize investments
                total_invested / 1000000,  # Total invested in millions
                avg_transaction_amount / 100000,  # Avg transaction in 100k
                transaction_frequency / 5,  # Normalize frequency
                risk_tolerance,
                # Additional features
                0.0, 0.0, 0.0, 0.0, 0.0  # Padding to reach 15 features
            ]
            
            return torch.tensor(features[:15], dtype=torch.float32)
            
        except Exception as e:
            logger.error(f"Error extracting user features: {str(e)}")
            return torch.zeros(15, dtype=torch.float32)
    
    def get_market_features(self):
        """Get current market features (simulated for now)"""
        try:
            # In a real implementation, this would fetch live market data
            # For now, we'll simulate market conditions
            
            # Simulate market indicators
            treasury_bill_rate = 0.12  # 12% p.a.
            market_volatility = 0.15  # 15% volatility
            inflation_rate = 0.18  # 18% inflation
            gdp_growth = 0.03  # 3% GDP growth
            exchange_rate_stability = 0.8  # 80% stable
            interest_rate_environment = 0.14  # 14% base rate
            market_sentiment = 0.7  # 70% positive
            sector_performance = 0.65  # 65% performance
            regulatory_environment = 0.9  # 90% favorable
            economic_outlook = 0.75  # 75% positive
            
            features = [
                treasury_bill_rate,
                market_volatility,
                inflation_rate,
                gdp_growth,
                exchange_rate_stability,
                interest_rate_environment,
                market_sentiment,
                sector_performance,
                regulatory_environment,
                economic_outlook
            ]
            
            return torch.tensor(features, dtype=torch.float32)
            
        except Exception as e:
            logger.error(f"Error getting market features: {str(e)}")
            return torch.zeros(10, dtype=torch.float32)
    
    def get_investment_recommendations(self, user):
        """Get personalized investment recommendations"""
        try:
            user_features = self.get_user_features(user)
            market_features = self.get_market_features()
            
            # Add batch dimension
            user_features = user_features.unsqueeze(0).to(self.device)
            market_features = market_features.unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                recommendations = self.model(user_features, market_features)
                recommendation_probs = recommendations[0].cpu().numpy()
            
            # Create recommendation dictionary
            recommendations_dict = dict(zip(self.investment_types, recommendation_probs))
            
            # Add confidence and reasoning
            best_investment = max(recommendations_dict.items(), key=lambda x: x[1])
            
            return {
                'recommendations': recommendations_dict,
                'best_investment': best_investment[0],
                'confidence': best_investment[1],
                'reasoning': self._generate_reasoning(user, recommendations_dict),
                'last_updated': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting investment recommendations: {str(e)}")
            return {
                'recommendations': {
                    'treasury_bills': 0.25,
                    'mutual_funds': 0.25,
                    'government_bonds': 0.25,
                    'short_term_placements': 0.25
                },
                'best_investment': 'treasury_bills',
                'confidence': 0.25,
                'reasoning': 'Unable to generate personalized recommendations',
                'last_updated': timezone.now()
            }
    
    def _generate_reasoning(self, user, recommendations):
        """Generate reasoning for recommendations"""
        try:
            account = user.xysave_account
            balance = account.balance.amount
            
            reasoning = []
            
            if recommendations['treasury_bills'] > 0.3:
                reasoning.append("Treasury bills offer stable returns with government backing")
            
            if recommendations['mutual_funds'] > 0.3:
                reasoning.append("Mutual funds provide diversification and professional management")
            
            if recommendations['government_bonds'] > 0.3:
                reasoning.append("Government bonds are low-risk with predictable returns")
            
            if recommendations['short_term_placements'] > 0.3:
                reasoning.append("Short-term placements offer quick returns with flexibility")
            
            if balance < 100000:
                reasoning.append("Consider starting with smaller, safer investments")
            elif balance > 1000000:
                reasoning.append("You have significant capital for diversified investments")
            
            return " | ".join(reasoning) if reasoning else "Based on your profile and market conditions"
            
        except Exception as e:
            logger.error(f"Error generating reasoning: {str(e)}")
            return "Based on your profile and market conditions"
    
    def train_model(self, training_data):
        """Train the investment recommendation model"""
        try:
            # This would be implemented with actual training data
            # For now, we'll just save the current model
            torch.save(self.model.state_dict(), 'bank/pytorch_models/investment_recommendations.pth')
            logger.info("Investment recommendation model saved")
        except Exception as e:
            logger.error(f"Error training model: {str(e)}") 