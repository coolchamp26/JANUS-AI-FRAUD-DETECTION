"""
JANUS-AI: Module 4 - NLP-Based Document & Tender Analysis
Detects copy-paste tenders, vague specifications, and document anomalies
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

class NLPDocumentAnalyzer:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.vague_keywords = [
            'as per requirement', 'as needed', 'standard', 'normal',
            'usual', 'appropriate', 'suitable', 'adequate', 'necessary',
            'proper', 'reasonable', 'satisfactory', 'acceptable'
        ]
        
    def detect_vague_language(self, text):
        """Detect vague or non-specific language in tender documents"""
        if pd.isna(text):
            return 0
        
        text_lower = text.lower()
        vague_count = sum(1 for keyword in self.vague_keywords if keyword in text_lower)
        
        # Additional vagueness indicators
        word_count = len(text.split())
        
        if word_count < 20:  # Very short description
            vague_count += 3
        
        # Check for lack of numbers (specifications usually have numbers)
        numbers = re.findall(r'\d+', text)
        if len(numbers) == 0 and word_count > 10:
            vague_count += 2
        
        # Score: 0-100
        vagueness_score = min(100, vague_count * 15)
        return vagueness_score
    
    def detect_copy_paste_tenders(self, tenders_df):
        """Detect tenders with suspiciously similar descriptions"""
        descriptions = tenders_df['description'].fillna('')
        specifications = tenders_df['specifications'].fillna('')
        
        # Combine description and specifications
        full_text = descriptions + ' ' + specifications
        
        # Compute TF-IDF and similarity matrix
        tfidf_matrix = self.vectorizer.fit_transform(full_text)
        similarity_matrix = cosine_similarity(tfidf_matrix)
        
        # Find highly similar pairs (threshold: 0.85)
        similar_pairs = []
        n = len(tenders_df)
        
        for i in range(n):
            for j in range(i+1, n):
                similarity = similarity_matrix[i, j]
                
                if similarity > 0.85:  # High similarity threshold
                    similar_pairs.append({
                        'tender_1': tenders_df.iloc[i]['tender_id'],
                        'tender_2': tenders_df.iloc[j]['tender_id'],
                        'similarity_score': similarity,
                        'dept_1': tenders_df.iloc[i]['department'],
                        'dept_2': tenders_df.iloc[j]['department'],
                        'value_1': tenders_df.iloc[i]['estimated_value'],
                        'value_2': tenders_df.iloc[j]['estimated_value']
                    })
        
        return pd.DataFrame(similar_pairs)
    
    def analyze_deadline_feasibility(self, tenders_df):
        """Analyze if tender deadlines are unrealistically short"""
        tenders_df = tenders_df.copy()
        tenders_df['published_date'] = pd.to_datetime(tenders_df['published_date'])
        tenders_df['deadline'] = pd.to_datetime(tenders_df['deadline'])
        
        tenders_df['days_to_deadline'] = (
            tenders_df['deadline'] - tenders_df['published_date']
        ).dt.days
        
        # Score based on deadline
        tenders_df['deadline_risk_score'] = 0
        tenders_df.loc[tenders_df['days_to_deadline'] < 7, 'deadline_risk_score'] = 80
        tenders_df.loc[
            (tenders_df['days_to_deadline'] >= 7) & (tenders_df['days_to_deadline'] < 15),
            'deadline_risk_score'
        ] = 50
        tenders_df.loc[
            (tenders_df['days_to_deadline'] >= 15) & (tenders_df['days_to_deadline'] < 21),
            'deadline_risk_score'
        ] = 25
        
        return tenders_df[['tender_id', 'days_to_deadline', 'deadline_risk_score']]
    
    def analyze_value_deviation(self, tenders_df):
        """Detect tenders where award amount significantly differs from estimate"""
        tenders_df = tenders_df.copy()
        
        tenders_df['value_deviation_pct'] = (
            (tenders_df['award_amount'] - tenders_df['estimated_value']) / 
            tenders_df['estimated_value'] * 100
        )
        
        # High deviation is suspicious (either too low = dumping, or too high = overpricing)
        tenders_df['value_deviation_score'] = np.abs(tenders_df['value_deviation_pct']).clip(0, 100)
        
        return tenders_df[['tender_id', 'value_deviation_pct', 'value_deviation_score']]
    
    def detect_specification_manipulation(self, tenders_df):
        """Detect specifications designed to favor specific vendors"""
        manipulation_indicators = []
        
        for _, tender in tenders_df.iterrows():
            score = 0
            reasons = []
            
            spec_text = str(tender['specifications']).lower()
            desc_text = str(tender['description']).lower()
            combined_text = spec_text + ' ' + desc_text
            
            # Indicator 1: Mentions specific brands/models
            brand_keywords = ['brand', 'model no', 'part no', 'serial', 'make']
            if any(keyword in combined_text for keyword in brand_keywords):
                score += 30
                reasons.append('Contains brand/model specifications')
            
            # Indicator 2: Overly specific technical requirements
            technical_specificity = len(re.findall(r'\d+\.\d+', combined_text))
            if technical_specificity > 5:
                score += 25
                reasons.append('Highly specific technical parameters')
            
            # Indicator 3: Geographic restrictions
            if 'local' in combined_text or 'nearby' in combined_text or 'same city' in combined_text:
                score += 35
                reasons.append('Geographic restrictions')
            
            # Indicator 4: Prior experience requirements that are too specific
            if 'similar project' in combined_text or 'exact experience' in combined_text:
                score += 20
                reasons.append('Restrictive experience requirements')
            
            manipulation_indicators.append({
                'tender_id': tender['tender_id'],
                'manipulation_score': min(100, score),
                'manipulation_reasons': ', '.join(reasons) if reasons else 'None'
            })
        
        return pd.DataFrame(manipulation_indicators)
    
    def analyze_title_description_mismatch(self, tenders_df):
        """Detect when title and description don't match (possible copy-paste error)"""
        mismatches = []
        
        for _, tender in tenders_df.iterrows():
            title = str(tender['title']).lower()
            description = str(tender['description']).lower()
            
            # Extract key terms from title
            title_terms = set(re.findall(r'\b[a-z]{4,}\b', title))
            
            # Check if title terms appear in description
            matching_terms = sum(1 for term in title_terms if term in description)
            mismatch_score = 0
            
            if len(title_terms) > 0:
                match_ratio = matching_terms / len(title_terms)
                if match_ratio < 0.5:  # Less than 50% of title terms in description
                    mismatch_score = 70
            
            mismatches.append({
                'tender_id': tender['tender_id'],
                'mismatch_score': mismatch_score
            })
        
        return pd.DataFrame(mismatches)
    
    def aggregate_nlp_scores(self, tenders_df):
        """Aggregate all NLP signals into unified score"""
        results = tenders_df[['tender_id', 'title', 'department', 'estimated_value', 'winner_vendor_id']].copy()
        
        # Get all NLP analyses
        print("Detecting vague language...")
        results['vagueness_score'] = tenders_df['description'].apply(self.detect_vague_language)
        results['spec_vagueness_score'] = tenders_df['specifications'].apply(self.detect_vague_language)
        
        print("Analyzing deadlines...")
        deadline_analysis = self.analyze_deadline_feasibility(tenders_df)
        results = results.merge(deadline_analysis, on='tender_id', how='left')
        
        print("Analyzing value deviations...")
        value_analysis = self.analyze_value_deviation(tenders_df)
        results = results.merge(value_analysis, on='tender_id', how='left')
        
        print("Detecting specification manipulation...")
        manipulation_analysis = self.detect_specification_manipulation(tenders_df)
        results = results.merge(manipulation_analysis, on='tender_id', how='left')
        
        print("Analyzing title-description mismatch...")
        mismatch_analysis = self.analyze_title_description_mismatch(tenders_df)
        results = results.merge(mismatch_analysis, on='tender_id', how='left')
        
        print("Detecting copy-paste tenders...")
        similar_tenders = self.detect_copy_paste_tenders(tenders_df)
        
        # Flag tenders that appear in similar pairs
        if len(similar_tenders) > 0:
            similar_tender_ids = set(similar_tenders['tender_1']) | set(similar_tenders['tender_2'])
            results['is_copy_paste'] = results['tender_id'].isin(similar_tender_ids)
        else:
            results['is_copy_paste'] = False
        
        # Compute composite NLP anomaly score
        results['nlp_anomaly_score'] = (
            results['vagueness_score'] * 0.15 +
            results['spec_vagueness_score'] * 0.15 +
            results['deadline_risk_score'] * 0.20 +
            results['value_deviation_score'] * 0.20 +
            results['manipulation_score'] * 0.20 +
            results['mismatch_score'] * 0.10
        )
        
        # Boost score for copy-paste tenders
        results.loc[results['is_copy_paste'], 'nlp_anomaly_score'] += 30
        
        # Normalize
        results['nlp_anomaly_score'] = results['nlp_anomaly_score'].clip(0, 100)
        
        return results, similar_tenders
    
    def get_top_nlp_anomalies(self, results, top_n=20):
        """Get most suspicious document patterns"""
        return results.nlargest(top_n, 'nlp_anomaly_score')

# Example usage
if __name__ == '__main__':
    # Load tender data
    tenders = pd.read_csv('tenders.csv')
    
    # Initialize and run analyzer
    analyzer = NLPDocumentAnalyzer()
    results, similar_tenders = analyzer.aggregate_nlp_scores(tenders)
    
    # Get top anomalies
    top_anomalies = analyzer.get_top_nlp_anomalies(results, top_n=20)
    
    print("\n=== TOP 20 NLP DOCUMENT ANOMALIES ===\n")
    for idx, row in top_anomalies.iterrows():
        print(f"Tender: {row['tender_id']}")
        print(f"  NLP Score: {row['nlp_anomaly_score']:.1f}/100")
        print(f"  Title: {row['title']}")
        print(f"  Department: {row['department']}")
        print(f"  Vagueness: {row['vagueness_score']:.1f}")
        print(f"  Deadline Risk: {row['deadline_risk_score']:.1f}")
        print(f"  Value Deviation: {row['value_deviation_pct']:.1f}%")
        print()
    
    if len(similar_tenders) > 0:
        print("\n=== COPY-PASTE TENDER PAIRS ===")
        print(similar_tenders.head(10))
    
    # Save results
    results.to_csv('nlp_anomalies.csv', index=False)
    similar_tenders.to_csv('similar_tenders.csv', index=False)
    
    print("\nNLP analysis complete. Results saved.")
