"""
JANUS-AI: Main Pipeline
Complete end-to-end fraud detection pipeline
"""

import sys
import time
from datetime import datetime

# Import all modules
from financial_anomaly import FinancialAnomalyDetector
from network_detector import NetworkCollusionDetector
from temporal_detector import TemporalAnomalyDetector
from nlp_detector import NLPDocumentAnalyzer
from citizen_feedback import CitizenFeedbackAnalyzer
from meta_fraud_engine import MetaFraudRiskEngine
from explainability_engine import ExplainabilityEngine
from data_generator import DataGenerator


def print_banner():
    """Print JANUS-AI banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║           🔍 JANUS-AI FRAUD DETECTION SYSTEM 🔍              ║
    ║                                                               ║
    ║     AI-Powered Public Fraud & Anomaly Detection              ║
    ║     National Level Hackathon Submission                      ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_step(step_num, step_name):
    """Print pipeline step"""
    print(f"\n{'='*70}")
    print(f"STEP {step_num}: {step_name}")
    print(f"{'='*70}")

def main():
    """Run complete fraud detection pipeline"""
    start_time = time.time()
    
    print_banner()
    print(f"\nPipeline started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # STEP 1: Generate synthetic data
        print_step(1, "DATA GENERATION")
        generator = DataGenerator(seed=42)
        datasets = generator.generate_all()
        
        for name, df in datasets.items():
            df.to_csv(f'{name}.csv', index=False)
            print(f"  ✓ Generated {name}.csv: {len(df)} records")
        
        # STEP 2: Financial anomaly detection
        print_step(2, "FINANCIAL ANOMALY DETECTION")
        financial_detector = FinancialAnomalyDetector(contamination=0.15)
        financial_results = financial_detector.detect_anomalies(datasets['transactions'])
        financial_results.to_csv('financial_anomalies.csv', index=False)
        anomaly_count = financial_results['is_anomaly'].sum()
        print(f"  ✓ Detected {anomaly_count} financial anomalies")
        print(f"  ✓ Saved to financial_anomalies.csv")
        
        # STEP 3: Temporal pattern detection
        print_step(3, "TEMPORAL PATTERN DETECTION")
        temporal_detector = TemporalAnomalyDetector(spike_threshold=3.0)
        temporal_results = temporal_detector.aggregate_temporal_scores(datasets['transactions'])
        temporal_results.to_csv('temporal_anomalies.csv', index=False)
        high_temporal = len(temporal_results[temporal_results['temporal_anomaly_score'] > 50])
        print(f"  ✓ Analyzed temporal patterns")
        print(f"  ✓ Found {high_temporal} high-risk temporal anomalies")
        print(f"  ✓ Saved to temporal_anomalies.csv")
        
        # STEP 4: Network & collusion detection
        print_step(4, "NETWORK & COLLUSION DETECTION")
        network_detector = NetworkCollusionDetector()
        network_detector.build_transaction_network(datasets['transactions'], datasets['vendors'])
        
        repeated_pairs = network_detector.detect_repeated_interactions()
        repeated_pairs.to_csv('repeated_pairs.csv', index=False)
        
        hub_officials = network_detector.detect_hub_officials()
        hub_officials.to_csv('hub_officials.csv', index=False)
        
        clusters = network_detector.detect_vendor_clusters()
        clusters.to_csv('vendor_clusters.csv', index=False)
        
        network_results = network_detector.aggregate_network_scores(datasets['transactions'])
        network_results.to_csv('network_anomalies.csv', index=False)
        
        print(f"  ✓ Built transaction network graph")
        print(f"  ✓ Found {len(repeated_pairs)} suspicious vendor-official pairs")
        print(f"  ✓ Identified {len(hub_officials)} hub officials")
        print(f"  ✓ Detected {len(clusters)} vendor clusters")
        print(f"  ✓ Saved network analysis results")
        
        # STEP 5: NLP document analysis
        print_step(5, "NLP DOCUMENT ANALYSIS")

        nlp_analyzer = NLPDocumentAnalyzer()
        nlp_results, similar_tenders = nlp_analyzer.aggregate_nlp_scores(datasets['tenders'])

        # Merge NLP anomaly score back into tenders (CORRECT WAY)
        datasets['tenders'] = datasets['tenders'].merge(
            nlp_results[['tender_id', 'nlp_anomaly_score']],
            on='tender_id',
            how='left'
        )

        # Fill missing NLP scores safely
        datasets['tenders']['nlp_anomaly_score'] = datasets['tenders']['nlp_anomaly_score'].fillna(0)
        datasets['tenders'].to_csv('tenders.csv', index=False)

        nlp_results.to_csv('nlp_anomalies.csv', index=False)
        similar_tenders.to_csv('similar_tenders.csv', index=False)

        high_nlp = len(nlp_results[nlp_results['nlp_anomaly_score'] > 50])
        print(f"  ✓ Analyzed {len(datasets['tenders'])} tender documents")
        print(f"  ✓ Found {len(similar_tenders)} copy-paste tender pairs")
        print(f"  ✓ Flagged {high_nlp} suspicious tenders")
        print(f"  ✓ Saved NLP analysis results")

        # --- SCHEMA NORMALIZATION (CRITICAL) ---
        # Ensure vendor_id exists consistently for meta + explainability layers

        if 'vendor_id' not in datasets['tenders'].columns and 'winner_vendor_id' in datasets['tenders'].columns:
            datasets['tenders']['vendor_id'] = datasets['tenders']['winner_vendor_id']

        if 'vendor_id' not in datasets['transactions'].columns and 'vendor_id' in datasets['transactions'].columns:
            pass  # already correct

        # Persist normalized tenders
        datasets['tenders'].to_csv('tenders.csv', index=False)

        
        # STEP 6: Citizen feedback analysis
        print_step(6, "CITIZEN FEEDBACK ANALYSIS")
        citizen_analyzer = CitizenFeedbackAnalyzer()
        citizen_results, mismatch, no_feedback, spikes = citizen_analyzer.aggregate_citizen_scores(
            datasets['feedback'],
            datasets['transactions']
        )
        citizen_results.to_csv('citizen_feedback_scores.csv', index=False)
        mismatch.to_csv('spending_satisfaction_mismatch.csv', index=False)
        no_feedback.to_csv('no_feedback_projects.csv', index=False)
        
        high_mismatch = len(mismatch[mismatch['mismatch_score'] > 50])
        print(f"  ✓ Analyzed citizen feedback data")
        print(f"  ✓ Found {high_mismatch} spending-satisfaction mismatches")
        print(f"  ✓ Identified {len(no_feedback)} high-spending projects with no feedback")
        print(f"  ✓ Saved citizen feedback analysis")
        
        # STEP 7: Meta fraud risk scoring
        print_step(7, "META FRAUD RISK SCORING")

        meta_engine = MetaFraudRiskEngine()

        # Run meta analysis
        unified_scores, case_summaries, statistics = meta_engine.run_complete_analysis()

        # Save outputs
        unified_scores.to_csv('meta_fraud_scores.csv', index=False)
        case_summaries.to_csv('investigation_cases.csv', index=False)

        print(f"  ✓ Aggregated scores from all 5 modules")
        print(f"  ✓ Computed unified fraud risk scores")
        print(f"  ✓ Generated {len(case_summaries)} prioritized investigation cases")
        print(f"  ✓ Saved meta fraud analysis")

        
        # STEP 8: Generate explanations
        print_step(8, "EXPLAINABILITY REPORT GENERATION")
        
        # Load all data for explainability
        import pandas as pd
        all_data = {
            'transactions': datasets['transactions'],
            'financial_scores': financial_results,
            'temporal_scores': temporal_results,
            'network_scores': network_results,
            'nlp_scores': nlp_results,
            'citizen_scores': citizen_results,
            'meta_scores': unified_scores,
            'tenders': datasets['tenders'],
            'feedback': datasets['feedback'],
            'repeated_pairs': repeated_pairs,
            'hub_officials': hub_officials,
            'mismatch_analysis': mismatch
        }
        
        explainer = ExplainabilityEngine()
        
        # Generate reports for top 10 cases
        for i in range(min(10, len(case_summaries))):
            case = case_summaries.iloc[i]
            explanation = explainer.generate_complete_explanation(
                case['transaction_id'],
                all_data
            )
            report = explainer.generate_human_readable_report(explanation)
            
            with open(f"reports/fraud_report_{case['case_id']}.txt", 'w') as f:
                f.write(report)
        
        print(f"  ✓ Generated detailed explanations for top 10 cases")
        print(f"  ✓ Saved reports to reports/ directory")
        
        # Display final statistics
        print_step(9, "FINAL STATISTICS")
        print(f"\n  Total Transactions Analyzed: {statistics['total_transactions']:,}")
        print(f"  Total Flagged (Score > 50): {statistics['total_flagged']:,}")
        print(f"\n  Risk Distribution:")
        print(f"    CRITICAL: {statistics['critical_risk']:,}")
        print(f"    HIGH: {statistics['high_risk']:,}")
        print(f"    MEDIUM: {statistics['medium_risk']:,}")
        print(f"    LOW: {statistics['low_risk']:,}")
        print(f"    MINIMAL: {statistics['minimal_risk']:,}")
        print(f"\n  Financial Impact:")
        print(f"    Total Transaction Amount: ${statistics['total_amount']:,.2f}")
        print(f"    Flagged Transaction Amount: ${statistics['flagged_amount']:,.2f}")
        print(f"    Potential Fraud Percentage: {statistics['flagged_amount']/statistics['total_amount']*100:.1f}%")
        print(f"\n  Strong Evidence Cases:")
        print(f"    Multi-Module Flags (3+): {statistics['multi_module_flags']:,}")
        
        # Calculate execution time
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n{'='*70}")
        print(f"✅ PIPELINE COMPLETED SUCCESSFULLY")
        print(f"{'='*70}")
        print(f"\n  Execution Time: {execution_time:.2f} seconds")
        print(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n  All results saved to CSV files")
        print(f"  Launch dashboard: streamlit run dashboard_app.py")
        print(f"\n{'='*70}\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # Create reports directory
    import os
    os.makedirs('reports', exist_ok=True)
    
    # Run pipeline
    success = main()
    
    if not success:
        sys.exit(1)
