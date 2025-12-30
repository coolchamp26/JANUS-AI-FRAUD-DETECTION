"""
JANUS-AI: Module 5 - Citizen Feedback Analysis
Analyzes sentiment, complaint spikes, and spending-satisfaction mismatches
"""

import pandas as pd
import numpy as np
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

class CitizenFeedbackAnalyzer:
    def __init__(self):
        self.positive_words = [
            'good', 'excellent', 'satisfied', 'improved', 'quality',
            'timely', 'complete', 'happy', 'better', 'great'
        ]
        self.negative_words = [
            'poor', 'bad', 'delay', 'incomplete', 'substandard',
            'misused', 'disappeared', 'corruption', 'fraud', 'waste'
        ]
        
    def analyze_sentiment(self, text):
        """Simple rule-based sentiment analysis"""
        if pd.isna(text):
            return 'Neutral', 0
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in self.positive_words if word in text_lower)
        negative_count = sum(1 for word in self.negative_words if word in text_lower)
        
        if negative_count > positive_count:
            sentiment = 'Negative'
            score = -min(100, negative_count * 20)
        elif positive_count > negative_count:
            sentiment = 'Positive'
            score = min(100, positive_count * 20)
        else:
            sentiment = 'Neutral'
            score = 0
        
        return sentiment, score
    
    def detect_complaint_spikes(self, feedback_df):
        """Detect unusual spikes in complaints for departments/projects"""
        feedback_df = feedback_df.copy()
        feedback_df['date'] = pd.to_datetime(feedback_df['date'])
        
        # Weekly complaint aggregation by department
        feedback_df['week'] = feedback_df['date'].dt.to_period('W')
        
        weekly_complaints = feedback_df.groupby(['week', 'department']).agg({
            'feedback_id': 'count',
            'severity': 'mean'
        }).reset_index()
        weekly_complaints.columns = ['week', 'department', 'complaint_count', 'avg_severity']
        
        # Compute baselines per department
        dept_baselines = weekly_complaints.groupby('department').agg({
            'complaint_count': ['mean', 'std']
        }).reset_index()
        dept_baselines.columns = ['department', 'baseline_count', 'baseline_std']
        
        # Merge and compute z-scores
        weekly_complaints = weekly_complaints.merge(dept_baselines, on='department')
        weekly_complaints['complaint_zscore'] = (
            (weekly_complaints['complaint_count'] - weekly_complaints['baseline_count']) /
            (weekly_complaints['baseline_std'] + 1e-6)
        )
        
        # Identify spike weeks (z-score > 2)
        spike_weeks = weekly_complaints[weekly_complaints['complaint_zscore'] > 2].copy()
        
        return spike_weeks
    
    def analyze_spending_satisfaction_mismatch(self, feedback_df, transactions_df):
        """Detect projects with high spending but poor citizen satisfaction"""
        # Aggregate spending by project
        project_spending = transactions_df.groupby('project_id').agg({
            'amount': 'sum',
            'department': 'first'
        }).reset_index()
        project_spending.columns = ['project_id', 'total_spending', 'department']
        
        # Aggregate feedback by project
        project_feedback = feedback_df.groupby('project_id').agg({
            'feedback_id': 'count',
            'severity': 'mean',
            'sentiment': lambda x: (x == 'Negative').sum() / len(x) if len(x) > 0 else 0
        }).reset_index()
        project_feedback.columns = ['project_id', 'feedback_count', 'avg_severity', 'negative_ratio']
        
        # Merge spending and feedback
        mismatch_analysis = project_spending.merge(project_feedback, on='project_id', how='left')
        mismatch_analysis['negative_ratio'] = mismatch_analysis['negative_ratio'].fillna(0)
        mismatch_analysis['avg_severity'] = mismatch_analysis['avg_severity'].fillna(5)
        
        # Compute mismatch score: high spending + high negative feedback
        # Normalize spending to 0-100 scale
        max_spending = mismatch_analysis['total_spending'].max()
        mismatch_analysis['spending_score'] = (
            mismatch_analysis['total_spending'] / max_spending * 100
        )
        
        mismatch_analysis['feedback_negativity_score'] = (
            mismatch_analysis['negative_ratio'] * 100
        )
        
        # Mismatch score: high spending + high negativity
        mismatch_analysis['mismatch_score'] = (
            mismatch_analysis['spending_score'] * 0.5 +
            mismatch_analysis['feedback_negativity_score'] * 0.5
        )
        
        return mismatch_analysis
    
    def detect_no_feedback_high_spending(self, transactions_df, feedback_df):
        """Detect high-value projects with suspiciously zero citizen feedback"""
        # Projects with spending
        projects_with_spending = set(transactions_df['project_id'].unique())
        
        # Projects with feedback
        projects_with_feedback = set(feedback_df['project_id'].unique())
        
        # Projects with NO feedback
        projects_no_feedback = projects_with_spending - projects_with_feedback
        
        # Get spending for these projects
        no_feedback_projects = transactions_df[
            transactions_df['project_id'].isin(projects_no_feedback)
        ].groupby('project_id').agg({
            'amount': 'sum',
            'department': 'first'
        }).reset_index()
        
        no_feedback_projects.columns = ['project_id', 'total_spending', 'department']
        
        # High spending with no feedback is suspicious
        no_feedback_projects['no_feedback_risk_score'] = np.clip(
            no_feedback_projects['total_spending'] / 100000,
            0, 100
        )
        
        return no_feedback_projects
    
    def analyze_temporal_feedback_patterns(self, feedback_df, transactions_df):
        """Analyze timing of feedback relative to project completion/payment"""
        feedback_df = feedback_df.copy()
        feedback_df['date'] = pd.to_datetime(feedback_df['date'])
        
        transactions_df = transactions_df.copy()
        transactions_df['date'] = pd.to_datetime(transactions_df['date'])
        
        # Get last transaction date per project (proxy for project completion)
        project_completion = transactions_df.groupby('project_id')['date'].max().reset_index()
        project_completion.columns = ['project_id', 'completion_date']
        
        # Merge with feedback
        feedback_timing = feedback_df.merge(project_completion, on='project_id', how='left')
        
        # Compute days between completion and feedback
        feedback_timing['days_after_completion'] = (
            feedback_timing['date'] - feedback_timing['completion_date']
        ).dt.days
        
        # Negative feedback soon after completion is concerning
        feedback_timing['timing_risk_score'] = 0
        
        negative_soon = (
            (feedback_timing['sentiment'] == 'Negative') &
            (feedback_timing['days_after_completion'] >= 0) &
            (feedback_timing['days_after_completion'] <= 90)
        )
        
        feedback_timing.loc[negative_soon, 'timing_risk_score'] = 70
        
        return feedback_timing
    
    def aggregate_citizen_scores(self, feedback_df, transactions_df):
        """Aggregate all citizen feedback signals"""
        # Get all analyses
        print("Analyzing sentiment...")
        feedback_df = feedback_df.copy()
        sentiment_results = feedback_df['complaint_text'].apply(
            lambda x: pd.Series(self.analyze_sentiment(x), index=['sentiment_analyzed', 'sentiment_score'])
        )
        feedback_df = pd.concat([feedback_df, sentiment_results], axis=1)
        
        print("Detecting complaint spikes...")
        spike_weeks = self.detect_complaint_spikes(feedback_df)
        
        print("Analyzing spending-satisfaction mismatch...")
        mismatch_analysis = self.analyze_spending_satisfaction_mismatch(feedback_df, transactions_df)
        
        print("Detecting projects with no feedback...")
        no_feedback_projects = self.detect_no_feedback_high_spending(transactions_df, feedback_df)
        
        print("Analyzing feedback timing...")
        timing_analysis = self.analyze_temporal_feedback_patterns(feedback_df, transactions_df)
        
        # Create project-level scores
        project_scores = mismatch_analysis[['project_id', 'department', 'mismatch_score']].copy()
        
        # Add no-feedback risk
        no_feedback_risk = no_feedback_projects[['project_id', 'no_feedback_risk_score']]
        project_scores = project_scores.merge(
            no_feedback_risk,
            on='project_id',
            how='outer'
        ).fillna(0)
        
        # Compute composite citizen feedback score
        project_scores['citizen_feedback_score'] = (
            project_scores['mismatch_score'] * 0.6 +
            project_scores['no_feedback_risk_score'] * 0.4
        ).clip(0, 100)
        
        # Map back to transactions
        transactions_with_feedback = transactions_df.merge(
            project_scores[['project_id', 'citizen_feedback_score']],
            on='project_id',
            how='left'
        )
        transactions_with_feedback['citizen_feedback_score'] = (
            transactions_with_feedback['citizen_feedback_score'].fillna(0)
        )
        
        results = transactions_with_feedback[[
            'transaction_id', 'project_id', 'department',
            'vendor_id', 'amount', 'citizen_feedback_score'
        ]].copy()
        
        return results, mismatch_analysis, no_feedback_projects, spike_weeks
    
    def get_top_citizen_anomalies(self, results, top_n=20):
        """Get transactions with worst citizen feedback signals"""
        return results.nlargest(top_n, 'citizen_feedback_score')

# Example usage
if __name__ == '__main__':
    # Load data
    feedback = pd.read_csv('feedback.csv')
    transactions = pd.read_csv('transactions.csv')
    
    # Initialize and run analyzer
    analyzer = CitizenFeedbackAnalyzer()
    results, mismatch, no_feedback, spikes = analyzer.aggregate_citizen_scores(
        feedback, transactions
    )
    
    # Get top anomalies
    top_anomalies = analyzer.get_top_citizen_anomalies(results, top_n=20)
    
    print("\n=== TOP 20 CITIZEN FEEDBACK ANOMALIES ===\n")
    for idx, row in top_anomalies.iterrows():
        print(f"Transaction: {row['transaction_id']}")
        print(f"  Citizen Score: {row['citizen_feedback_score']:.1f}/100")
        print(f"  Project: {row['project_id']}")
        print(f"  Department: {row['department']}")
        print(f"  Amount: ${row['amount']:,.2f}")
        print()
    
    print("\n=== SPENDING-SATISFACTION MISMATCHES ===")
    print(mismatch.nlargest(10, 'mismatch_score'))
    
    print("\n=== HIGH SPENDING WITH NO FEEDBACK ===")
    print(no_feedback.nlargest(10, 'no_feedback_risk_score'))
    
    # Save results
    results.to_csv('citizen_feedback_scores.csv', index=False)
    mismatch.to_csv('spending_satisfaction_mismatch.csv', index=False)
    no_feedback.to_csv('no_feedback_projects.csv', index=False)
    
    print("\nCitizen feedback analysis complete. Results saved.")
