"""
JANUS-AI: Module 2 - Temporal Pattern & Spike Detection
Detects abnormal timing patterns, transaction spikes, and suspicious quiet periods
"""

import pandas as pd
import numpy as np
from scipy import stats
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')

class TemporalAnomalyDetector:
    def __init__(self, spike_threshold=3.0, window_days=30):
        """
        spike_threshold: Z-score threshold for spike detection
        window_days: Rolling window for pattern analysis
        """
        self.spike_threshold = spike_threshold
        self.window_days = window_days
        
    def detect_transaction_spikes(self, df):
        """Detect unusual spikes in transaction volume or amount"""
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Daily aggregation
        daily_stats = df.groupby(df['date'].dt.date).agg({
            'transaction_id': 'count',
            'amount': 'sum'
        }).reset_index()
        daily_stats.columns = ['date', 'txn_count', 'total_amount']
        
        # Compute rolling statistics
        daily_stats['rolling_mean_count'] = daily_stats['txn_count'].rolling(
            window=self.window_days, min_periods=7
        ).mean()
        daily_stats['rolling_std_count'] = daily_stats['txn_count'].rolling(
            window=self.window_days, min_periods=7
        ).std()
        
        daily_stats['rolling_mean_amount'] = daily_stats['total_amount'].rolling(
            window=self.window_days, min_periods=7
        ).mean()
        daily_stats['rolling_std_amount'] = daily_stats['total_amount'].rolling(
            window=self.window_days, min_periods=7
        ).std()
        
        # Z-scores for spike detection
        daily_stats['count_zscore'] = (
            (daily_stats['txn_count'] - daily_stats['rolling_mean_count']) / 
            (daily_stats['rolling_std_count'] + 1e-6)
        )
        
        daily_stats['amount_zscore'] = (
            (daily_stats['total_amount'] - daily_stats['rolling_mean_amount']) / 
            (daily_stats['rolling_std_amount'] + 1e-6)
        )
        
        # Identify spike days
        daily_stats['is_spike'] = (
            (daily_stats['count_zscore'] > self.spike_threshold) | 
            (daily_stats['amount_zscore'] > self.spike_threshold)
        )
        
        return daily_stats
    
    def detect_rapid_succession(self, df):
        """Detect rapid succession of transactions (potential automated fraud)"""
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        rapid_succession_flags = []
        
        # Check for transactions within 1 hour of each other by same vendor or official
        for entity_col in ['vendor_id', 'official_id']:
            entity_groups = df.groupby(entity_col)
            
            for entity_id, group in entity_groups:
                if len(group) < 2:
                    continue
                
                time_diffs = group['date'].diff()
                rapid_txns = time_diffs < timedelta(hours=1)
                
                if rapid_txns.sum() > 0:
                    rapid_indices = group[rapid_txns].index
                    for idx in rapid_indices:
                        rapid_succession_flags.append({
                            'transaction_id': df.loc[idx, 'transaction_id'],
                            'entity_type': entity_col,
                            'entity_id': entity_id,
                            'time_diff_minutes': time_diffs.loc[idx].total_seconds() / 60
                        })
        
        return pd.DataFrame(rapid_succession_flags)
    
    def detect_unusual_timing(self, df):
        """Detect transactions at unusual times (weekends, late night)"""
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        df['hour'] = df['date'].dt.hour
        df['day_of_week'] = df['date'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'] >= 5
        df['is_late_night'] = (df['hour'] < 6) | (df['hour'] > 20)
        
        # Score unusual timing
        df['timing_risk_score'] = 0
        df.loc[df['is_weekend'], 'timing_risk_score'] += 30
        df.loc[df['is_late_night'], 'timing_risk_score'] += 40
        df.loc[df['is_weekend'] & df['is_late_night'], 'timing_risk_score'] = 80
        
        return df[['transaction_id', 'date', 'timing_risk_score', 'is_weekend', 'is_late_night']]
    
    def detect_dormancy_followed_by_spike(self, df):
        """Detect vendors/officials with long dormancy then sudden activity"""
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        dormancy_alerts = []
        
        for entity_col in ['vendor_id', 'official_id']:
            entity_groups = df.groupby(entity_col)
            
            for entity_id, group in entity_groups:
                if len(group) < 2:
                    continue
                
                time_diffs = group['date'].diff()
                
                # Long dormancy (>180 days) followed by activity
                long_gaps = time_diffs > timedelta(days=180)
                
                if long_gaps.sum() > 0:
                    gap_indices = group[long_gaps].index
                    for idx in gap_indices:
                        dormancy_alerts.append({
                            'transaction_id': df.loc[idx, 'transaction_id'],
                            'entity_type': entity_col,
                            'entity_id': entity_id,
                            'dormancy_days': time_diffs.loc[idx].days,
                            'amount': df.loc[idx, 'amount']
                        })
        
        return pd.DataFrame(dormancy_alerts)
    
    def detect_end_of_period_clustering(self, df):
        """Detect suspicious clustering near fiscal year/quarter end"""
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        df['day_of_month'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        
        # Flag transactions in last 5 days of quarter-end months
        quarter_end_months = [3, 6, 9, 12]
        df['is_quarter_end'] = (
            (df['month'].isin(quarter_end_months)) & 
            (df['day_of_month'] >= 26)
        )
        
        # Compute clustering score
        df['period_end_risk'] = df['is_quarter_end'].astype(int) * 50
        
        return df[['transaction_id', 'date', 'period_end_risk', 'is_quarter_end']]
    
    def aggregate_temporal_scores(self, df):
        """Aggregate all temporal signals into unified score"""
        df = df.copy()
        
        # Get all temporal features
        spike_data = self.detect_transaction_spikes(df)
        timing_data = self.detect_unusual_timing(df)
        period_end_data = self.detect_end_of_period_clustering(df)
        rapid_succession = self.detect_rapid_succession(df)
        dormancy_data = self.detect_dormancy_followed_by_spike(df)
        
        # Merge spike information back to transactions
        df['date'] = pd.to_datetime(df['date'])
        df['date_only'] = df['date'].dt.date
        df = df.merge(
            spike_data[['date', 'is_spike', 'count_zscore', 'amount_zscore']],
            left_on='date_only',
            right_on='date',
            how='left',
            suffixes=('', '_spike')
        )
        
        # Merge timing data
        df = df.merge(timing_data, on='transaction_id', how='left', suffixes=('', '_timing'))
        
        # Merge period end data
        df = df.merge(period_end_data, on='transaction_id', how='left', suffixes=('', '_period'))
        
        # Flag rapid succession transactions
        df['is_rapid_succession'] = df['transaction_id'].isin(rapid_succession['transaction_id'])
        
        # Flag dormancy revival
        df['is_dormancy_revival'] = df['transaction_id'].isin(dormancy_data['transaction_id'])
        
        # Compute composite temporal anomaly score
        df['temporal_anomaly_score'] = 0
        
        # Spike contribution
        df.loc[df['is_spike'] == True, 'temporal_anomaly_score'] += 40
        df['temporal_anomaly_score'] += df['count_zscore'].fillna(0).clip(0, 5) * 5
        
        # Timing contribution
        df['temporal_anomaly_score'] += df['timing_risk_score'].fillna(0)
        
        # Period end contribution
        df['temporal_anomaly_score'] += df['period_end_risk'].fillna(0)
        
        # Rapid succession contribution
        df.loc[df['is_rapid_succession'], 'temporal_anomaly_score'] += 35
        
        # Dormancy contribution
        df.loc[df['is_dormancy_revival'], 'temporal_anomaly_score'] += 30
        
        # Normalize to 0-100
        df['temporal_anomaly_score'] = df['temporal_anomaly_score'].clip(0, 100)
        
        results = df[[
            'transaction_id', 'date', 'amount', 'vendor_id', 'official_id',
            'temporal_anomaly_score', 'is_spike', 'is_rapid_succession',
            'is_dormancy_revival', 'timing_risk_score', 'period_end_risk'
        ]].copy()
        
        return results
    
    def get_top_temporal_anomalies(self, results, top_n=20):
        """Get most suspicious temporal patterns"""
        return results.nlargest(top_n, 'temporal_anomaly_score')

# Example usage
if __name__ == '__main__':
    # Load transaction data
    transactions = pd.read_csv('transactions.csv')
    
    # Initialize and run detector
    detector = TemporalAnomalyDetector(spike_threshold=3.0)
    results = detector.aggregate_temporal_scores(transactions)
    
    # Get top anomalies
    top_anomalies = detector.get_top_temporal_anomalies(results, top_n=20)
    
    print("\n=== TOP 20 TEMPORAL ANOMALIES ===\n")
    for idx, row in top_anomalies.iterrows():
        print(f"Transaction: {row['transaction_id']}")
        print(f"  Temporal Score: {row['temporal_anomaly_score']:.1f}/100")
        print(f"  Date: {row['date']}")
        print(f"  Amount: ${row['amount']:,.2f}")
        print(f"  Spike Event: {row['is_spike']}")
        print(f"  Rapid Succession: {row['is_rapid_succession']}")
        print()
    
    # Save results
    results.to_csv('temporal_anomalies.csv', index=False)
    print(f"\nTemporal analysis complete. Results saved.")
