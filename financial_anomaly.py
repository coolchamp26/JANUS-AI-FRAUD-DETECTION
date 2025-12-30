"""
JANUS-AI: Module 1 - Financial Anomaly Detection
Uses Isolation Forest and Autoencoder for transaction anomaly detection
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

class FinancialAnomalyDetector:
    def __init__(self, contamination=0.1):
        """
        contamination: Expected proportion of anomalies in dataset
        """
        self.contamination = contamination
        self.isolation_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.dept_baselines = {}
        
    def compute_department_baselines(self, df):
        """Compute baseline statistics for each department"""
        for dept in df['department'].unique():
            dept_data = df[df['department'] == dept]['amount']
            self.dept_baselines[dept] = {
                'mean': dept_data.mean(),
                'median': dept_data.median(),
                'std': dept_data.std(),
                'q1': dept_data.quantile(0.25),
                'q3': dept_data.quantile(0.75),
                'iqr': dept_data.quantile(0.75) - dept_data.quantile(0.25)
            }
    
    def engineer_features(self, df):
        """Create features for anomaly detection"""
        features = pd.DataFrame()
        
        # Amount-based features
        features['amount'] = df['amount']
        features['log_amount'] = np.log1p(df['amount'])
        
        # Department baseline deviation
        features['dept_mean_deviation'] = df.apply(
            lambda row: (row['amount'] - self.dept_baselines[row['department']]['mean']) / 
                       (self.dept_baselines[row['department']]['std'] + 1e-6),
            axis=1
        )
        
        features['dept_median_deviation'] = df.apply(
            lambda row: abs(row['amount'] - self.dept_baselines[row['department']]['median']) / 
                       (self.dept_baselines[row['department']]['median'] + 1e-6),
            axis=1
        )
        
        # Round number detection (suspicious patterns)
        features['is_round_number'] = df['amount'].apply(
            lambda x: 1 if x % 100000 == 0 or x % 50000 == 0 else 0
        )
        
        # IQR-based outlier score
        features['iqr_score'] = df.apply(
            lambda row: max(0, (row['amount'] - self.dept_baselines[row['department']]['q3']) / 
                           (self.dept_baselines[row['department']]['iqr'] + 1e-6)),
            axis=1
        )
        
        # Time-based features
        df['date'] = pd.to_datetime(df['date'])
        features['day_of_week'] = df['date'].dt.dayofweek
        features['month'] = df['date'].dt.month
        features['is_weekend'] = (features['day_of_week'] >= 5).astype(int)
        
        # Payment mode encoding (some modes riskier than others)
        payment_risk = {'Bank Transfer': 0, 'Digital Payment': 0, 'Cheque': 0.5, 'LC': 0.3}
        features['payment_risk'] = df['payment_mode'].map(payment_risk).fillna(0.5)
        
        # Vendor transaction frequency (new vendors are riskier)
        vendor_counts = df['vendor_id'].value_counts()
        features['vendor_frequency'] = df['vendor_id'].map(vendor_counts)
        features['is_new_vendor'] = (features['vendor_frequency'] <= 2).astype(int)
        
        # Category encoding
        features['category_encoded'] = pd.Categorical(df['category']).codes
        
        return features
    
    def detect_anomalies(self, df):
        """Main detection pipeline"""
        print("Computing department baselines...")
        self.compute_department_baselines(df)
        
        print("Engineering features...")
        features = self.engineer_features(df)
        
        print("Scaling features...")
        features_scaled = self.scaler.fit_transform(features)
        
        print("Running Isolation Forest...")
        predictions = self.isolation_forest.fit_predict(features_scaled)
        anomaly_scores = self.isolation_forest.score_samples(features_scaled)
        
        # Convert to 0-100 scale (higher = more anomalous)
        # Isolation Forest scores are negative, so we invert and normalize
        anomaly_scores_normalized = ((anomaly_scores - anomaly_scores.min()) / 
                                     (anomaly_scores.max() - anomaly_scores.min()))
        anomaly_scores_normalized = (1 - anomaly_scores_normalized) * 100
        
        # Create results dataframe
        results = pd.DataFrame({
            'transaction_id': df['transaction_id'],
            'is_anomaly': predictions == -1,
            'anomaly_score': anomaly_scores_normalized,
            'amount': df['amount'],
            'department': df['department'],
            'vendor_id': df['vendor_id'],
            'official_id': df['official_id'],
            'date': df['date']
        })
        
        # Add feature importance for explainability
        results['dept_deviation'] = features['dept_mean_deviation'].abs()
        results['is_round_number'] = features['is_round_number']
        results['is_new_vendor'] = features['is_new_vendor']
        results['iqr_score'] = features['iqr_score']
        
        return results
    
    def get_top_anomalies(self, results, top_n=20):
        """Get most suspicious transactions"""
        return results.nlargest(top_n, 'anomaly_score')
    
    def explain_anomaly(self, transaction_row, features_row):
        """Generate human-readable explanation"""
        reasons = []
        
        if features_row['dept_deviation'] > 2:
            reasons.append(f"Amount is {features_row['dept_deviation']:.1f}σ above department average")
        
        if features_row['is_round_number'] == 1:
            reasons.append("Transaction is a suspicious round number")
        
        if features_row['is_new_vendor'] == 1:
            reasons.append("Vendor has very few transactions (possible ghost vendor)")
        
        if features_row['iqr_score'] > 3:
            reasons.append(f"Amount is extreme outlier (IQR score: {features_row['iqr_score']:.1f})")
        
        if not reasons:
            reasons.append("Multiple weak signals combining into anomaly pattern")
        
        return reasons

# Example usage
if __name__ == '__main__':
    # Load transaction data
    transactions = pd.read_csv('transactions.csv')
    
    # Initialize and run detector
    detector = FinancialAnomalyDetector(contamination=0.15)
    results = detector.detect_anomalies(transactions)
    
    # Get top anomalies
    top_anomalies = detector.get_top_anomalies(results, top_n=20)
    
    print("\n=== TOP 20 FINANCIAL ANOMALIES ===\n")
    for idx, row in top_anomalies.iterrows():
        print(f"Transaction: {row['transaction_id']}")
        print(f"  Anomaly Score: {row['anomaly_score']:.1f}/100")
        print(f"  Amount: ${row['amount']:,.2f}")
        print(f"  Department: {row['department']}")
        print(f"  Vendor: {row['vendor_id']}")
        print()
    
    # Save results
    results.to_csv('financial_anomalies.csv', index=False)
    print(f"\nDetected {results['is_anomaly'].sum()} anomalies out of {len(results)} transactions")
    print("Results saved to financial_anomalies.csv")
