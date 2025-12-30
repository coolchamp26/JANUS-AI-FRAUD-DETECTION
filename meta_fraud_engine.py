"""
JANUS-AI: Meta Fraud Risk Scoring Engine
Combines signals from all modules into unified fraud risk score
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class MetaFraudRiskEngine:
    def __init__(self):
        # Weights for each module (must sum to 1.0)
        self.module_weights = {
            'financial': 0.25,
            'temporal': 0.20,
            'network': 0.25,
            'nlp': 0.15,
            'citizen': 0.15
        }
        
        # Risk thresholds
        self.thresholds = {
            'low': 30,
            'medium': 50,
            'high': 70,
            'critical': 85
        }
        
    def load_all_scores(self):
        """Load scores from all modules"""
        print("Loading module scores...")
        
        financial_scores = pd.read_csv('financial_anomalies.csv')
        temporal_scores = pd.read_csv('temporal_anomalies.csv')
        network_scores = pd.read_csv('network_anomalies.csv')
        citizen_scores = pd.read_csv('citizen_feedback_scores.csv')
        
        # For NLP, we need to map tenders to transactions
        nlp_scores = pd.read_csv('nlp_anomalies.csv')
        tenders = pd.read_csv('tenders.csv')
        transactions = pd.read_csv('transactions.csv')
        
        return {
            'financial': financial_scores,
            'temporal': temporal_scores,
            'network': network_scores,
            'nlp': nlp_scores,
            'citizen': citizen_scores,
            'tenders': tenders,
            'transactions': transactions
        }
    
    def map_tender_scores_to_transactions(self, transactions, tenders, nlp_scores):
        """Map NLP scores from tenders to transactions via vendor matching"""
        # Get tender-vendor mapping
        tender_vendor_map = tenders[['tender_id', 'winner_vendor_id', 'nlp_anomaly_score']].copy()
        tender_vendor_map = tender_vendor_map.merge(
            nlp_scores[['tender_id', 'nlp_anomaly_score']],
            on='tender_id',
            how='left',
            suffixes=('', '_nlp')
        )
        
        # Use NLP score from nlp_scores if available, else from tenders
        tender_vendor_map['nlp_score'] = tender_vendor_map['nlp_anomaly_score_nlp'].fillna(
            tender_vendor_map['nlp_anomaly_score']
        ).fillna(0)
        
        # Map to transactions by vendor
        vendor_nlp_scores = tender_vendor_map.groupby('winner_vendor_id')['nlp_score'].max().reset_index()
        vendor_nlp_scores.columns = ['vendor_id', 'nlp_anomaly_score']
        
        transactions_with_nlp = transactions.merge(
            vendor_nlp_scores,
            on='vendor_id',
            how='left'
        )
        transactions_with_nlp['nlp_anomaly_score'] = transactions_with_nlp['nlp_anomaly_score'].fillna(0)
        
        return transactions_with_nlp[['transaction_id', 'vendor_id', 'nlp_anomaly_score']]
    
    def merge_all_scores(self, data):
        """Merge scores from all modules"""
        print("Merging all scores...")
        
        transactions = data['transactions']
        
        # Start with financial scores (has all transactions)
        unified = data['financial'][[
            'transaction_id', 'anomaly_score', 'amount', 'department',
            'vendor_id', 'official_id', 'date'
        ]].copy()
        unified.rename(columns={'anomaly_score': 'financial_score'}, inplace=True)
        
        # Merge temporal scores
        temporal = data['temporal'][['transaction_id', 'temporal_anomaly_score']].copy()
        unified = unified.merge(temporal, on='transaction_id', how='left')
        unified['temporal_anomaly_score'] = unified['temporal_anomaly_score'].fillna(0)
        
        # Merge network scores
        network = data['network'][['transaction_id', 'network_anomaly_score']].copy()
        unified = unified.merge(network, on='transaction_id', how='left')
        unified['network_anomaly_score'] = unified['network_anomaly_score'].fillna(0)
        
        # Map and merge NLP scores
        nlp_mapped = self.map_tender_scores_to_transactions(
            transactions,
            data['tenders'],
            data['nlp']
        )
        unified = unified.merge(nlp_mapped, on='transaction_id', how='left')
        unified['nlp_anomaly_score'] = unified['nlp_anomaly_score'].fillna(0)
        
        # Merge citizen scores
        citizen = data['citizen'][['transaction_id', 'citizen_feedback_score']].copy()
        unified = unified.merge(citizen, on='transaction_id', how='left')
        unified['citizen_feedback_score'] = unified['citizen_feedback_score'].fillna(0)
        
        return unified
    
    def compute_meta_fraud_score(self, unified_df):
        """Compute weighted meta fraud risk score"""
        print("Computing meta fraud risk scores...")
        
        unified_df['meta_fraud_score'] = (
            unified_df['financial_score'] * self.module_weights['financial'] +
            unified_df['temporal_anomaly_score'] * self.module_weights['temporal'] +
            unified_df['network_anomaly_score'] * self.module_weights['network'] +
            unified_df['nlp_anomaly_score'] * self.module_weights['nlp'] +
            unified_df['citizen_feedback_score'] * self.module_weights['citizen']
        )
        
        # Ensure score is 0-100
        unified_df['meta_fraud_score'] = unified_df['meta_fraud_score'].clip(0, 100)
        
        return unified_df
    
    def classify_risk_level(self, unified_df):
        """Classify transactions into risk categories"""
        def assign_risk_level(score):
            if score >= self.thresholds['critical']:
                return 'CRITICAL'
            elif score >= self.thresholds['high']:
                return 'HIGH'
            elif score >= self.thresholds['medium']:
                return 'MEDIUM'
            elif score >= self.thresholds['low']:
                return 'LOW'
            else:
                return 'MINIMAL'
        
        unified_df['risk_level'] = unified_df['meta_fraud_score'].apply(assign_risk_level)
        
        return unified_df
    
    def prioritize_cases(self, unified_df):
        """Prioritize cases for investigation"""
        # Add priority score based on multiple factors
        unified_df['investigation_priority'] = 0
        
        # Factor 1: Meta fraud score (primary)
        unified_df['investigation_priority'] += unified_df['meta_fraud_score']
        
        # Factor 2: Amount (higher amounts = higher priority)
        max_amount = unified_df['amount'].max()
        unified_df['amount_priority'] = (unified_df['amount'] / max_amount) * 20
        unified_df['investigation_priority'] += unified_df['amount_priority']
        
        # Factor 3: Multiple module flags (stronger evidence)
        unified_df['num_modules_flagged'] = (
            (unified_df['financial_score'] > 50).astype(int) +
            (unified_df['temporal_anomaly_score'] > 50).astype(int) +
            (unified_df['network_anomaly_score'] > 50).astype(int) +
            (unified_df['nlp_anomaly_score'] > 50).astype(int) +
            (unified_df['citizen_feedback_score'] > 50).astype(int)
        )
        unified_df['investigation_priority'] += unified_df['num_modules_flagged'] * 10
        
        # Normalize to 0-100
        max_priority = unified_df['investigation_priority'].max()
        if max_priority > 0:
            unified_df['investigation_priority'] = (
                unified_df['investigation_priority'] / max_priority * 100
            )
        
        return unified_df
    
    def generate_case_summaries(self, unified_df, top_n=50):
        """Generate investigation case summaries for top risks"""
        top_cases = unified_df.nlargest(top_n, 'investigation_priority')
        
        case_summaries = []
        
        for idx, case in top_cases.iterrows():
            # Identify which modules flagged this transaction
            flagged_modules = []
            if case['financial_score'] > 50:
                flagged_modules.append(f"Financial ({case['financial_score']:.1f})")
            if case['temporal_anomaly_score'] > 50:
                flagged_modules.append(f"Temporal ({case['temporal_anomaly_score']:.1f})")
            if case['network_anomaly_score'] > 50:
                flagged_modules.append(f"Network ({case['network_anomaly_score']:.1f})")
            if case['nlp_anomaly_score'] > 50:
                flagged_modules.append(f"NLP ({case['nlp_anomaly_score']:.1f})")
            if case['citizen_feedback_score'] > 50:
                flagged_modules.append(f"Citizen ({case['citizen_feedback_score']:.1f})")
            
            summary = {
                'case_id': f"CASE_{idx+1:04d}",
                'transaction_id': case['transaction_id'],
                'risk_level': case['risk_level'],
                'meta_fraud_score': case['meta_fraud_score'],
                'investigation_priority': case['investigation_priority'],
                'amount': case['amount'],
                'department': case['department'],
                'vendor_id': (
                    case['vendor_id']
                    if 'vendor_id' in case.index
                    else case['winner_vendor_id']
                    if 'winner_vendor_id' in case.index
                    else 'UNKNOWN'
                ),
                'official_id': case['official_id'],
                'date': case['date'],
                'flagged_modules': ', '.join(flagged_modules) if flagged_modules else 'Multiple weak signals',
                'num_modules_flagged': case['num_modules_flagged']
            }

            
            case_summaries.append(summary)
        
        return pd.DataFrame(case_summaries)
    
    def generate_statistics(self, unified_df):
        """Generate overall fraud detection statistics"""
        stats = {
            'total_transactions': len(unified_df),
            'critical_risk': len(unified_df[unified_df['risk_level'] == 'CRITICAL']),
            'high_risk': len(unified_df[unified_df['risk_level'] == 'HIGH']),
            'medium_risk': len(unified_df[unified_df['risk_level'] == 'MEDIUM']),
            'low_risk': len(unified_df[unified_df['risk_level'] == 'LOW']),
            'minimal_risk': len(unified_df[unified_df['risk_level'] == 'MINIMAL']),
            'total_flagged': len(unified_df[unified_df['meta_fraud_score'] > 50]),
            'total_amount': unified_df['amount'].sum(),
            'flagged_amount': unified_df[unified_df['meta_fraud_score'] > 50]['amount'].sum(),
            'avg_fraud_score': unified_df['meta_fraud_score'].mean(),
            'multi_module_flags': len(unified_df[unified_df['num_modules_flagged'] >= 3])
        }
        
        return stats
    
    def run_complete_analysis(self):
        """Run complete meta fraud analysis"""
        # Load all data
        data = self.load_all_scores()
        
        # Merge scores
        unified = self.merge_all_scores(data)
        
        # Compute meta score
        unified = self.compute_meta_fraud_score(unified)
        
        # Classify risk
        unified = self.classify_risk_level(unified)
        
        # Prioritize cases
        unified = self.prioritize_cases(unified)
        
        # Generate case summaries
        case_summaries = self.generate_case_summaries(unified, top_n=100)
        
        # Generate statistics
        stats = self.generate_statistics(unified)
        
        return unified, case_summaries, stats

# Example usage
if __name__ == '__main__':
    # Initialize engine
    engine = MetaFraudRiskEngine()
    
    # Run complete analysis
    unified_scores, case_summaries, statistics = engine.run_complete_analysis()
    
    # Display statistics
    print("\n" + "="*60)
    print("JANUS-AI FRAUD DETECTION SUMMARY")
    print("="*60)
    print(f"Total Transactions Analyzed: {statistics['total_transactions']:,}")
    print(f"Total Flagged (Score > 50): {statistics['total_flagged']:,}")
    print(f"\nRisk Distribution:")
    print(f"  CRITICAL: {statistics['critical_risk']:,}")
    print(f"  HIGH: {statistics['high_risk']:,}")
    print(f"  MEDIUM: {statistics['medium_risk']:,}")
    print(f"  LOW: {statistics['low_risk']:,}")
    print(f"  MINIMAL: {statistics['minimal_risk']:,}")
    print(f"\nFinancial Impact:")
    print(f"  Total Amount: ${statistics['total_amount']:,.2f}")
    print(f"  Flagged Amount: ${statistics['flagged_amount']:,.2f}")
    print(f"  Potential Fraud %: {statistics['flagged_amount']/statistics['total_amount']*100:.1f}%")
    print(f"\nStrong Evidence Cases:")
    print(f"  Multi-Module Flags (3+): {statistics['multi_module_flags']:,}")
    print("="*60)
    
    # Display top cases
    print("\n" + "="*60)
    print("TOP 20 PRIORITY INVESTIGATION CASES")
    print("="*60)
    
    for idx, case in case_summaries.head(20).iterrows():
        print(f"\n{case['case_id']}: {case['transaction_id']}")
        print(f"  Risk Level: {case['risk_level']}")
        print(f"  Meta Fraud Score: {case['meta_fraud_score']:.1f}/100")
        print(f"  Investigation Priority: {case['investigation_priority']:.1f}/100")
        print(f"  Amount: ${case['amount']:,.2f}")
        print(f"  Department: {case['department']}")
        print(f"  Vendor: {case['vendor_id']}")
        print(f"  Official: {case['official_id']}")
        print(f"  Modules Flagged: {case['flagged_modules']}")
    
    # Save results
    unified_scores.to_csv('meta_fraud_scores.csv', index=False)
    case_summaries.to_csv('investigation_cases.csv', index=False)
    
    print("\n\nAnalysis complete. Results saved to:")
    print("  - meta_fraud_scores.csv")
    print("  - investigation_cases.csv")
