"""
Customer Insights Service for XySave using PyTorch
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

class CustomerBehaviorModel(nn.Module):
    """PyTorch model for customer behavior analysis"""
    
    def __init__(self, input_size=25, hidden_size=256, num_clusters=5):
        super(CustomerBehaviorModel, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.BatchNorm1d(hidden_size),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.BatchNorm1d(hidden_size // 2),
            nn.Linear(hidden_size // 2, num_clusters)
        )
        
    def forward(self, x):
        return self.encoder(x)

class XySaveCustomerInsightsService:
    """Service for customer behavior insights using PyTorch"""
    
    def __init__(self):
        self.model = CustomerBehaviorModel()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Try to load pre-trained model, otherwise use random weights
        try:
            self.model.load_state_dict(torch.load('bank/pytorch_models/customer_behavior.pth', map_location=self.device))
            logger.info("Loaded pre-trained customer behavior model")
        except FileNotFoundError:
            logger.warning("No pre-trained model found. Using random weights.")
        
        self.model.eval()
        
        # Behavior clusters
        self.behavior_clusters = [
            'risk_tolerance',
            'savings_habit', 
            'investment_preference',
            'loyalty_score',
            'churn_risk'
        ]
    
    def extract_customer_features(self, user):
        """Extract comprehensive customer features"""
        try:
            account = user.xysave_account
            
            # Financial behavior features
            balance = account.balance.amount
            total_interest_earned = account.total_interest_earned.amount
            account_age_days = (timezone.now() - user.date_joined).days
            
            # Transaction behavior
            transactions = account.transactions.all().order_by('-created_at')[:100]
            total_transactions = transactions.count()
            
            if total_transactions == 0:
                return torch.zeros(25, dtype=torch.float32)
            
            # Transaction patterns
            deposit_transactions = transactions.filter(transaction_type='deposit')
            withdrawal_transactions = transactions.filter(transaction_type='withdrawal')
            
            avg_deposit = deposit_transactions.aggregate(avg=Avg('amount'))['avg'] or 0
            avg_withdrawal = withdrawal_transactions.aggregate(avg=Avg('amount'))['avg'] or 0
            deposit_frequency = deposit_transactions.count() / max(account_age_days, 1)
            withdrawal_frequency = withdrawal_transactions.count() / max(account_age_days, 1)
            
            # Savings behavior
            goals = user.xysave_goals.filter(is_active=True)
            total_goals = goals.count()
            completed_goals = goals.filter(current_amount__gte=F('target_amount')).count()
            goal_completion_rate = completed_goals / max(total_goals, 1)
            
            # Investment behavior
            investments = account.investments.filter(is_active=True)
            total_investments = investments.count()
            total_invested = investments.aggregate(total=Sum('amount_invested'))['total'] or 0
            investment_ratio = total_invested / max(balance + total_invested, 1)
            
            # Auto-save behavior
            auto_save_enabled = 1 if account.auto_save_enabled else 0
            auto_save_percentage = account.auto_save_percentage / 100
            
            # Time-based patterns
            recent_transactions = transactions[:30]
            transactions_this_month = recent_transactions.filter(
                created_at__month=timezone.now().month
            ).count()
            
            # Risk indicators
            large_transactions = transactions.filter(amount__gt=100000).count()
            large_transaction_ratio = large_transactions / max(total_transactions, 1)
            
            # Loyalty indicators
            days_since_last_transaction = (timezone.now() - transactions.first().created_at).days if transactions.exists() else account_age_days
            transaction_consistency = 1 - (days_since_last_transaction / max(account_age_days, 1))
            
            # Normalize features
            features = [
                balance / 1000000,  # Balance in millions
                total_interest_earned / 100000,  # Interest in 100k
                account_age_days / 365,  # Account age in years
                total_transactions / 100,  # Normalize transactions
                avg_deposit / 100000,  # Avg deposit in 100k
                avg_withdrawal / 100000,  # Avg withdrawal in 100k
                deposit_frequency * 30,  # Deposits per month
                withdrawal_frequency * 30,  # Withdrawals per month
                total_goals / 10,  # Normalize goals
                goal_completion_rate,
                total_investments / 10,  # Normalize investments
                investment_ratio,
                auto_save_enabled,
                auto_save_percentage,
                transactions_this_month / 30,  # Transactions per day this month
                large_transaction_ratio,
                transaction_consistency,
                # Additional behavioral features
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0  # Padding to reach 25 features
            ]
            
            return torch.tensor(features[:25], dtype=torch.float32)
            
        except Exception as e:
            logger.error(f"Error extracting customer features: {str(e)}")
            return torch.zeros(25, dtype=torch.float32)
    
    def analyze_customer_behavior(self, user):
        """Analyze customer behavior patterns"""
        try:
            features = self.extract_customer_features(user)
            features = features.unsqueeze(0).to(self.device)  # Add batch dimension
            
            with torch.no_grad():
                behavior_cluster = self.model(features)
                cluster_probabilities = F.softmax(behavior_cluster, dim=1)[0].cpu().numpy()
            
            # Create behavior analysis dictionary
            behavior_analysis = dict(zip(self.behavior_clusters, cluster_probabilities))
            
            return {
                'risk_tolerance': behavior_analysis['risk_tolerance'],
                'savings_habit': behavior_analysis['savings_habit'],
                'investment_preference': behavior_analysis['investment_preference'],
                'loyalty_score': behavior_analysis['loyalty_score'],
                'churn_risk': behavior_analysis['churn_risk'],
                'overall_score': np.mean(cluster_probabilities),
                'behavior_type': self._classify_behavior_type(behavior_analysis)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing customer behavior: {str(e)}")
            return {
                'risk_tolerance': 0.5,
                'savings_habit': 0.5,
                'investment_preference': 0.5,
                'loyalty_score': 0.5,
                'churn_risk': 0.5,
                'overall_score': 0.5,
                'behavior_type': 'balanced'
            }
    
    def _classify_behavior_type(self, behavior_analysis):
        """Classify customer behavior type based on analysis"""
        try:
            risk_tolerance = behavior_analysis['risk_tolerance']
            savings_habit = behavior_analysis['savings_habit']
            investment_preference = behavior_analysis['investment_preference']
            loyalty_score = behavior_analysis['loyalty_score']
            churn_risk = behavior_analysis['churn_risk']
            
            if savings_habit > 0.7 and churn_risk < 0.3:
                return 'conservative_saver'
            elif risk_tolerance > 0.7 and investment_preference > 0.6:
                return 'aggressive_investor'
            elif loyalty_score > 0.8 and savings_habit > 0.6:
                return 'loyal_customer'
            elif churn_risk > 0.7:
                return 'at_risk'
            elif savings_habit < 0.3 and investment_preference < 0.3:
                return 'inactive_user'
            else:
                return 'balanced'
                
        except Exception as e:
            logger.error(f"Error classifying behavior type: {str(e)}")
            return 'balanced'
    
    def get_personalized_recommendations(self, user):
        """Get personalized recommendations based on behavior analysis"""
        try:
            behavior = self.analyze_customer_behavior(user)
            account = user.xysave_account
            
            recommendations = []
            
            # Savings recommendations
            if behavior['savings_habit'] < 0.5:
                recommendations.append({
                    'type': 'savings',
                    'title': 'Improve Your Savings',
                    'description': 'Consider enabling auto-save to build consistent savings habits',
                    'priority': 'high'
                })
            
            if not account.auto_save_enabled and behavior['savings_habit'] < 0.7:
                recommendations.append({
                    'type': 'auto_save',
                    'title': 'Enable Auto-Save',
                    'description': 'Automatically save a percentage of your incoming funds',
                    'priority': 'medium'
                })
            
            # Investment recommendations
            if behavior['investment_preference'] < 0.4 and account.balance.amount > 50000:
                recommendations.append({
                    'type': 'investment',
                    'title': 'Start Investing',
                    'description': 'Consider diversifying your portfolio with our investment options',
                    'priority': 'medium'
                })
            
            # Goal recommendations
            if len(user.xysave_goals.filter(is_active=True)) == 0:
                recommendations.append({
                    'type': 'goal',
                    'title': 'Set Savings Goals',
                    'description': 'Create specific goals to stay motivated and track your progress',
                    'priority': 'high'
                })
            
            # Risk management recommendations
            if behavior['churn_risk'] > 0.6:
                recommendations.append({
                    'type': 'engagement',
                    'title': 'Stay Engaged',
                    'description': 'Explore our features to maximize your savings potential',
                    'priority': 'high'
                })
            
            # Loyalty recommendations
            if behavior['loyalty_score'] > 0.8:
                recommendations.append({
                    'type': 'premium',
                    'title': 'Premium Features',
                    'description': 'You qualify for premium features and higher interest rates',
                    'priority': 'low'
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {str(e)}")
            return []
    
    def get_customer_segment(self, user):
        """Get customer segment based on behavior analysis"""
        try:
            behavior = self.analyze_customer_behavior(user)
            account = user.xysave_account
            
            # Segment based on balance and behavior
            balance = account.balance.amount
            
            if balance > 1000000 and behavior['investment_preference'] > 0.6:
                return 'premium_investor'
            elif balance > 500000 and behavior['savings_habit'] > 0.7:
                return 'high_value_saver'
            elif balance > 100000 and behavior['loyalty_score'] > 0.6:
                return 'loyal_customer'
            elif balance < 50000 and behavior['churn_risk'] > 0.5:
                return 'at_risk'
            elif balance < 100000 and behavior['savings_habit'] < 0.4:
                return 'new_user'
            else:
                return 'regular_customer'
                
        except Exception as e:
            logger.error(f"Error getting customer segment: {str(e)}")
            return 'regular_customer'
    
    def train_model(self, training_data):
        """Train the customer behavior model"""
        try:
            # This would be implemented with actual training data
            # For now, we'll just save the current model
            torch.save(self.model.state_dict(), 'bank/pytorch_models/customer_behavior.pth')
            logger.info("Customer behavior model saved")
        except Exception as e:
            logger.error(f"Error training model: {str(e)}") 