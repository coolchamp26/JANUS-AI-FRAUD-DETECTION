"""
JANUS-AI: Explainability Engine
Provides human-readable explanations for fraud flags
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class ExplainabilityEngine:
    def __init__(self):
        pass
    
    def generate_financial_explanation(self, transaction, financial_scores):
        """Generate explanation for financial anomalies"""
        txn_financial = financial_scores[
            financial_scores['transaction_id'] == transaction['transaction_id']
        ]
        
        if len(txn_financial) == 0:
            return []
        
        row = txn_financial.iloc[0]
        explanations = []
        
        if row['dept_deviation'] > 2:
            explanations.append({
                'module': 'Financial',
                'severity': 'HIGH',
                'reason': f"Transaction amount is {row['dept_deviation']:.1f} standard deviations above the department baseline",
                'detail': f"Amount: ${row['amount']:,.2f}, Department: {row['department']}",
                'score_contribution': 25
            })
        
        if row['is_round_number'] == 1:
            explanations.append({
                'module': 'Financial',
                'severity': 'MEDIUM',
                'reason': "Transaction is a suspicious round number",
                'detail': f"Exact amount: ${row['amount']:,.2f}",
                'score_contribution': 15
            })
        
        if row['is_new_vendor'] == 1:
            explanations.append({
                'module': 'Financial',
                'severity': 'MEDIUM',
                'reason': "Vendor has very few transactions (potential ghost vendor)",
                'detail': f"Vendor ID: {row['vendor_id']}",
                'score_contribution': 20
            })
        
        if row['iqr_score'] > 3:
            explanations.append({
                'module': 'Financial',
                'severity': 'HIGH',
                'reason': "Transaction is an extreme statistical outlier",
                'detail': f"IQR Score: {row['iqr_score']:.1f}",
                'score_contribution': 20
            })
        
        return explanations
    
    def generate_temporal_explanation(self, transaction, temporal_scores):
        """Generate explanation for temporal anomalies"""
        txn_temporal = temporal_scores[
            temporal_scores['transaction_id'] == transaction['transaction_id']
        ]
        
        if len(txn_temporal) == 0:
            return []
        
        row = txn_temporal.iloc[0]
        explanations = []
        
        if row['is_spike']:
            explanations.append({
                'module': 'Temporal',
                'severity': 'HIGH',
                'reason': "Transaction occurred during abnormal spike in activity",
                'detail': f"Date: {row['date']}",
                'score_contribution': 30
            })
        
        if row['is_rapid_succession']:
            explanations.append({
                'module': 'Temporal',
                'severity': 'HIGH',
                'reason': "Transaction in rapid succession (potential automated fraud)",
                'detail': "Multiple transactions within 1 hour",
                'score_contribution': 25
            })
        
        if row['is_dormancy_revival']:
            explanations.append({
                'module': 'Temporal',
                'severity': 'MEDIUM',
                'reason': "Entity reactivated after long dormancy period",
                'detail': "Dormancy > 180 days",
                'score_contribution': 20
            })
        
        if row['timing_risk_score'] > 50:
            explanations.append({
                'module': 'Temporal',
                'severity': 'MEDIUM',
                'reason': "Transaction occurred at unusual time",
                'detail': "Weekend or late night transaction",
                'score_contribution': 15
            })
        
        if row['period_end_risk'] > 0:
            explanations.append({
                'module': 'Temporal',
                'severity': 'LOW',
                'reason': "Transaction near fiscal period end",
                'detail': "Last week of quarter",
                'score_contribution': 10
            })
        
        return explanations
    
    def generate_network_explanation(self, transaction, network_scores, repeated_pairs, hub_officials):
        """Generate explanation for network anomalies"""
        txn_network = network_scores[
            network_scores['transaction_id'] == transaction['transaction_id']
        ]
        
        if len(txn_network) == 0:
            return []
        
        row = txn_network.iloc[0]
        explanations = []
        
        if row['is_repeated_pair']:
            # Find the specific pair
            pair_info = repeated_pairs[
                (repeated_pairs['vendor_id'] == row['vendor_id']) &
                (repeated_pairs['official_id'] == row['official_id'])
            ]
            
            if len(pair_info) > 0:
                count = pair_info.iloc[0]['interaction_count']
                explanations.append({
                    'module': 'Network',
                    'severity': 'HIGH',
                    'reason': f"Vendor-official pair has {count} repeated interactions (collusion pattern)",
                    'detail': f"Vendor: {row['vendor_id']}, Official: {row['official_id']}",
                    'score_contribution': 35
                })
        
        if row['is_hub_official']:
            hub_info = hub_officials[hub_officials['official_id'] == row['official_id']]
            if len(hub_info) > 0:
                connections = hub_info.iloc[0]['vendor_connections']
                explanations.append({
                    'module': 'Network',
                    'severity': 'MEDIUM',
                    'reason': f"Official connected to {connections} different vendors (hub pattern)",
                    'detail': f"Official: {row['official_id']}",
                    'score_contribution': 25
                })
        
        if row['is_cluster_vendor']:
            explanations.append({
                'module': 'Network',
                'severity': 'HIGH',
                'reason': "Vendor belongs to suspicious cluster (potential shell company network)",
                'detail': f"Vendor: {row['vendor_id']}",
                'score_contribution': 30
            })
        
        return explanations
    
    def generate_nlp_explanation(self, transaction, nlp_scores, tenders):
        """Generate explanation for NLP anomalies"""

        # Resolve vendor ID safely (handles schema drift)
        vendor_id = (
            transaction['vendor_id']
            if 'vendor_id' in transaction.index
            else transaction['winner_vendor_id']
            if 'winner_vendor_id' in transaction.index
            else None
        )

        # If no vendor can be resolved, return no NLP explanations
        if vendor_id is None:
            return []

        # Find tenders related to this vendor
        related_tenders = tenders[tenders['winner_vendor_id'] == vendor_id]

        explanations = []

        for _, tender in related_tenders.iterrows():
            tender_nlp = nlp_scores[nlp_scores['tender_id'] == tender['tender_id']]

            if len(tender_nlp) == 0:
                continue

            nlp_row = tender_nlp.iloc[0]

            if nlp_row['vagueness_score'] > 50:
                explanations.append({
                    'module': 'NLP',
                    'severity': 'MEDIUM',
                    'reason': "Tender description is vague and non-specific",
                    'detail': f"Tender: {tender['tender_id']}, Vagueness Score: {nlp_row['vagueness_score']:.1f}",
                    'score_contribution': 15
                })

            if nlp_row['deadline_risk_score'] > 50:
                explanations.append({
                    'module': 'NLP',
                    'severity': 'HIGH',
                    'reason': f"Tender deadline unrealistically short ({nlp_row['days_to_deadline']} days)",
                    'detail': f"Tender: {tender['tender_id']}",
                    'score_contribution': 20
                })

            if abs(nlp_row['value_deviation_pct']) > 30:
                explanations.append({
                    'module': 'NLP',
                    'severity': 'HIGH',
                    'reason': f"Award amount deviates {nlp_row['value_deviation_pct']:.1f}% from estimate",
                    'detail': (
                        f"Tender: {tender['tender_id']}, "
                        f"Estimate: ${tender['estimated_value']:,.2f}, "
                        f"Award: ${tender['award_amount']:,.2f}"
                    ),
                    'score_contribution': 25
                })

            if nlp_row['manipulation_score'] > 50:
                explanations.append({
                    'module': 'NLP',
                    'severity': 'HIGH',
                    'reason': "Tender specifications may be manipulated to favor specific vendor",
                    'detail': f"Tender: {tender['tender_id']}, Manipulation indicators detected",
                    'score_contribution': 30
                })

            if nlp_row['is_copy_paste']:
                explanations.append({
                    'module': 'NLP',
                    'severity': 'MEDIUM',
                    'reason': "Tender appears to be copy-pasted from another tender",
                    'detail': f"Tender: {tender['tender_id']}",
                    'score_contribution': 20
                })

        return explanations

    
    def generate_citizen_explanation(self, transaction, citizen_scores, feedback, mismatch_analysis):
        """Generate explanation for citizen feedback anomalies"""
        txn_citizen = citizen_scores[
            citizen_scores['transaction_id'] == transaction['transaction_id']
        ]
        
        if len(txn_citizen) == 0:
            return []
        
        row = txn_citizen.iloc[0]
        explanations = []
        
        if row['citizen_feedback_score'] > 50:
            # Check mismatch analysis
            project_mismatch = mismatch_analysis[
                mismatch_analysis['project_id'] == row['project_id']
            ]
            
            if len(project_mismatch) > 0:
                mismatch = project_mismatch.iloc[0]
                
                if mismatch['negative_ratio'] > 0.5:
                    explanations.append({
                        'module': 'Citizen Feedback',
                        'severity': 'HIGH',
                        'reason': f"High spending with {mismatch['negative_ratio']*100:.0f}% negative citizen feedback",
                        'detail': f"Project: {row['project_id']}, Spending: ${mismatch['total_spending']:,.2f}",
                        'score_contribution': 35
                    })
                
                if mismatch['avg_severity'] > 7:
                    explanations.append({
                        'module': 'Citizen Feedback',
                        'severity': 'HIGH',
                        'reason': f"Complaints with high severity rating ({mismatch['avg_severity']:.1f}/10)",
                        'detail': f"Project: {row['project_id']}",
                        'score_contribution': 25
                    })
            
            # Check for no feedback on high spending
            if row['citizen_feedback_score'] > 60:
                project_feedback = feedback[feedback['project_id'] == row['project_id']]
                if len(project_feedback) == 0:
                    explanations.append({
                        'module': 'Citizen Feedback',
                        'severity': 'MEDIUM',
                        'reason': "High-value project with zero citizen feedback (suspicious silence)",
                        'detail': f"Project: {row['project_id']}, Amount: ${row['amount']:,.2f}",
                        'score_contribution': 30
                    })
        
        return explanations
    
    def generate_complete_explanation(self, transaction_id, all_data):
        """Generate complete explanation for a transaction"""
        # Load all necessary data
        transactions = all_data['transactions']
        financial_scores = all_data['financial_scores']
        temporal_scores = all_data['temporal_scores']
        network_scores = all_data['network_scores']
        nlp_scores = all_data['nlp_scores']
        citizen_scores = all_data['citizen_scores']
        meta_scores = all_data['meta_scores']
        tenders = all_data['tenders']
        feedback = all_data['feedback']
        repeated_pairs = all_data['repeated_pairs']
        hub_officials = all_data['hub_officials']
        mismatch_analysis = all_data['mismatch_analysis']
        
        # Get transaction details
        transaction = meta_scores[meta_scores['transaction_id'] == transaction_id]
        
        if len(transaction) == 0:
            return None
        
        transaction = transaction.iloc[0]
        
        # Generate explanations from each module
        financial_exp = self.generate_financial_explanation(transaction, financial_scores)
        temporal_exp = self.generate_temporal_explanation(transaction, temporal_scores)
        network_exp = self.generate_network_explanation(
            transaction, network_scores, repeated_pairs, hub_officials
        )
        nlp_exp = self.generate_nlp_explanation(transaction, nlp_scores, tenders)
        citizen_exp = self.generate_citizen_explanation(
            transaction, citizen_scores, feedback, mismatch_analysis
        )
        
        # Combine all explanations
        all_explanations = (
            financial_exp + temporal_exp + network_exp + nlp_exp + citizen_exp
        )
        
        # Sort by severity
        severity_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        all_explanations.sort(key=lambda x: severity_order.get(x['severity'], 3))
        
        # Create summary
        # Safely resolve vendor_id (handles schema drift)
        vendor_id = (
            transaction['vendor_id']
            if 'vendor_id' in transaction.index
            else transaction['winner_vendor_id']
            if 'winner_vendor_id' in transaction.index
            else 'UNKNOWN'
        )

        summary = {
            'transaction_id': transaction_id,
            'meta_fraud_score': transaction['meta_fraud_score'],
            'risk_level': transaction['risk_level'],
            'amount': transaction['amount'],
            'department': transaction['department'],
            'vendor_id': vendor_id,
            'official_id': transaction['official_id'],
            'date': transaction['date'],
            'num_flags': len(all_explanations),
            'explanations': all_explanations
        }

        return summary

    
    def generate_human_readable_report(self, explanation):
        """Generate human-readable audit report"""
        if explanation is None:
            return "Transaction not found."
        
        report = []
        report.append("="*80)
        report.append("JANUS-AI FRAUD INVESTIGATION REPORT")
        report.append("="*80)
        report.append("")
        report.append(f"Transaction ID: {explanation['transaction_id']}")
        report.append(f"Meta Fraud Risk Score: {explanation['meta_fraud_score']:.1f}/100")
        report.append(f"Risk Classification: {explanation['risk_level']}")
        report.append("")
        report.append("TRANSACTION DETAILS:")
        report.append(f"  Amount: ${explanation['amount']:,.2f}")
        report.append(f"  Department: {explanation['department']}")
        report.append(f"  Vendor: {explanation['vendor_id']}")
        report.append(f"  Approving Official: {explanation['official_id']}")
        report.append(f"  Date: {explanation['date']}")
        report.append("")
        report.append(f"NUMBER OF FLAGS: {explanation['num_flags']}")
        report.append("")
        report.append("DETAILED FINDINGS:")
        report.append("-"*80)
        
        for i, exp in enumerate(explanation['explanations'], 1):
            report.append(f"\n{i}. [{exp['module']}] {exp['severity']} SEVERITY")
            report.append(f"   Finding: {exp['reason']}")
            report.append(f"   Details: {exp['detail']}")
            report.append(f"   Score Impact: +{exp['score_contribution']} points")
        
        report.append("")
        report.append("="*80)
        report.append("RECOMMENDED ACTION:")
        
        if explanation['risk_level'] == 'CRITICAL':
            report.append("  IMMEDIATE INVESTIGATION REQUIRED")
            report.append("  - Freeze transaction if not yet processed")
            report.append("  - Initiate formal audit")
            report.append("  - Interview vendor and official")
        elif explanation['risk_level'] == 'HIGH':
            report.append("  PRIORITY INVESTIGATION")
            report.append("  - Request supporting documentation")
            report.append("  - Review related transactions")
            report.append("  - Schedule interview with stakeholders")
        elif explanation['risk_level'] == 'MEDIUM':
            report.append("  STANDARD REVIEW")
            report.append("  - Request additional documentation")
            report.append("  - Monitor for pattern development")
        else:
            report.append("  MONITORING RECOMMENDED")
            report.append("  - Add to watchlist")
            report.append("  - Review in quarterly audit")
        
        report.append("="*80)
        
        return "\n".join(report)

# Example usage
if __name__ == '__main__':
    # Load all data
    all_data = {
        'transactions': pd.read_csv('transactions.csv'),
        'financial_scores': pd.read_csv('financial_anomalies.csv'),
        'temporal_scores': pd.read_csv('temporal_anomalies.csv'),
        'network_scores': pd.read_csv('network_anomalies.csv'),
        'nlp_scores': pd.read_csv('nlp_anomalies.csv'),
        'citizen_scores': pd.read_csv('citizen_feedback_scores.csv'),
        'meta_scores': pd.read_csv('meta_fraud_scores.csv'),
        'tenders': pd.read_csv('tenders.csv'),
        'feedback': pd.read_csv('feedback.csv'),
        'repeated_pairs': pd.read_csv('repeated_pairs.csv'),
        'hub_officials': pd.read_csv('hub_officials.csv'),
        'mismatch_analysis': pd.read_csv('spending_satisfaction_mismatch.csv')
    }
    
    # Initialize engine
    engine = ExplainabilityEngine()
    
    # Get top fraud cases
    cases = pd.read_csv('investigation_cases.csv')
    
    # Generate explanations for top 5 cases
    print("\nGenerating detailed explanations for top 5 cases...\n")
    
    for i in range(min(5, len(cases))):
        case = cases.iloc[i]
        explanation = engine.generate_complete_explanation(
            case['transaction_id'],
            all_data
        )
        
        report = engine.generate_human_readable_report(explanation)
        print(report)
        print("\n\n")
        
        # Save individual report
        with open(f"fraud_report_{case['case_id']}.txt", 'w') as f:
            f.write(report)
    
    print("Explanation reports generated successfully.")
