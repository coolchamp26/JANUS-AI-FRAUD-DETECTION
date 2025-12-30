"""
JANUS-AI: Synthetic Dataset Generator
Generates realistic government transaction data with injected fraud patterns
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import string

class DataGenerator:
    def __init__(self, seed=42):
        np.random.seed(seed)
        random.seed(seed)
        
        # Configuration
        self.start_date = datetime(2022, 1, 1)
        self.end_date = datetime(2024, 12, 31)
        
        # Reference data
        self.departments = [
            'Public Works', 'Education', 'Healthcare', 'Transport',
            'Rural Development', 'Urban Planning', 'Welfare', 'Infrastructure'
        ]
        
        self.categories = [
            'Construction', 'Equipment', 'Services', 'Supplies',
            'Maintenance', 'Consulting', 'IT Systems', 'Training'
        ]
        
        self.payment_modes = ['Bank Transfer', 'Cheque', 'Digital Payment', 'LC']
        
    def generate_vendors(self, n_normal=150, n_fraud=20):
        """Generate vendor registry with fraud patterns"""
        vendors = []
        
        # Normal vendors
        for i in range(n_normal):
            vendor = {
                'vendor_id': f'VEN{str(i+1).zfill(5)}',
                'vendor_name': f'{random.choice(["Alpha", "Beta", "Gamma", "Delta", "Sigma"])} {random.choice(["Solutions", "Industries", "Services", "Enterprises"])} Pvt Ltd',
                'registration_date': self.start_date + timedelta(days=random.randint(0, 730)),
                'address': f'{random.randint(1,999)} {random.choice(["MG Road", "Park Street", "Station Road", "Mall Road"])}, {random.choice(["Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata"])}',
                'owner_name': f'{random.choice(["Rajesh", "Amit", "Priya", "Suresh", "Anjali"])} {random.choice(["Kumar", "Sharma", "Patel", "Singh", "Reddy"])}',
                'pan_number': ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)),
                'bank_account': ''.join(random.choices(string.digits, k=11)),
                'risk_history': 'Clean',
                'is_fraud': False
            }
            vendors.append(vendor)
        
        # Fraud Pattern 1: Ghost Vendors (no real address, recent registration)
        for i in range(n_fraud):
            vendor = {
                'vendor_id': f'VEN{str(n_normal+i+1).zfill(5)}',
                'vendor_name': f'{random.choice(["Quick", "Fast", "Rapid", "Swift"])} {random.choice(["Build", "Construct", "Supply"])} Co',
                'registration_date': self.end_date - timedelta(days=random.randint(30, 180)),
                'address': 'NA',  # Red flag
                'owner_name': ''.join(random.choices(string.ascii_uppercase, k=8)),  # Suspicious name
                'pan_number': 'XXXXX1234X',  # Invalid pattern
                'bank_account': ''.join(random.choices(string.digits, k=11)),
                'risk_history': 'Newly Registered',
                'is_fraud': True
            }
            vendors.append(vendor)
        
        return pd.DataFrame(vendors)
    
    def generate_officials(self, n=80):
        """Generate government officials"""
        officials = []
        
        for i in range(n):
            official = {
                'official_id': f'OFF{str(i+1).zfill(4)}',
                'name': f'{random.choice(["Dr.", "Mr.", "Ms.", ""])} {random.choice(["Rahul", "Sneha", "Vikram", "Kavita", "Arun"])} {random.choice(["Verma", "Gupta", "Nair", "Desai", "Iyer"])}',
                'department': random.choice(self.departments),
                'designation': random.choice(['Executive Engineer', 'Deputy Secretary', 'Project Director', 'Chief Accounts Officer', 'Superintendent']),
                'joining_date': self.start_date - timedelta(days=random.randint(365, 3650)),
                'salary_grade': random.randint(7, 14),
                'clearance_level': random.randint(1, 5)
            }
            officials.append(official)
        
        return pd.DataFrame(officials)
    
    def generate_transactions(self, vendors_df, officials_df, n_normal=2000, n_fraud=200):
        """Generate financial transactions with fraud patterns"""
        transactions = []
        
        normal_vendors = vendors_df[~vendors_df['is_fraud']]
        fraud_vendors = vendors_df[vendors_df['is_fraud']]
        
        # Baseline amounts per department
        dept_baselines = {dept: np.random.uniform(50000, 500000) for dept in self.departments}
        
        # Normal transactions
        for i in range(n_normal):
            dept = random.choice(self.departments)
            baseline = dept_baselines[dept]
            
            transaction = {
                'transaction_id': f'TXN{str(i+1).zfill(6)}',
                'date': self.start_date + timedelta(days=random.randint(0, 1095)),
                'department': dept,
                'project_id': f'PRJ{random.randint(1000, 9999)}',
                'vendor_id': random.choice(normal_vendors['vendor_id'].values),
                'official_id': random.choice(officials_df[officials_df['department'] == dept]['official_id'].values) if len(officials_df[officials_df['department'] == dept]) > 0 else random.choice(officials_df['official_id'].values),
                'amount': np.random.normal(baseline, baseline * 0.3),
                'category': random.choice(self.categories),
                'payment_mode': random.choice(self.payment_modes),
                'description': f'{random.choice(self.categories)} work for project',
                'is_fraud': False,
                'fraud_type': None
            }
            transactions.append(transaction)
        
        # Fraud Pattern 1: Ghost vendor transactions (inflated amounts)
        for i in range(n_fraud // 4):
            dept = random.choice(self.departments)
            baseline = dept_baselines[dept]
            
            transaction = {
                'transaction_id': f'TXN{str(n_normal+i+1).zfill(6)}',
                'date': self.end_date - timedelta(days=random.randint(10, 150)),
                'department': dept,
                'project_id': f'PRJ{random.randint(1000, 9999)}',
                'vendor_id': random.choice(fraud_vendors['vendor_id'].values),
                'official_id': random.choice(officials_df['official_id'].values),
                'amount': baseline * random.uniform(3, 8),  # 3-8x baseline
                'category': random.choice(self.categories),
                'payment_mode': random.choice(self.payment_modes),
                'description': 'Urgent procurement',
                'is_fraud': True,
                'fraud_type': 'ghost_vendor'
            }
            transactions.append(transaction)
        
        # Fraud Pattern 2: Round number anomalies
        for i in range(n_fraud // 4):
            dept = random.choice(self.departments)
            
            transaction = {
                'transaction_id': f'TXN{str(n_normal+n_fraud//4+i+1).zfill(6)}',
                'date': self.start_date + timedelta(days=random.randint(0, 1095)),
                'department': dept,
                'project_id': f'PRJ{random.randint(1000, 9999)}',
                'vendor_id': random.choice(normal_vendors['vendor_id'].values),
                'official_id': random.choice(officials_df['official_id'].values),
                'amount': random.choice([100000, 500000, 1000000, 2000000]),  # Exact round numbers
                'category': random.choice(self.categories),
                'payment_mode': random.choice(self.payment_modes),
                'description': 'Contract payment',
                'is_fraud': True,
                'fraud_type': 'round_number'
            }
            transactions.append(transaction)
        
        # Fraud Pattern 3: Collusion (same official, related vendors, short time span)
        collusion_official = random.choice(officials_df['official_id'].values)
        collusion_vendors = random.sample(list(normal_vendors['vendor_id'].values), 3)
        base_date = self.start_date + timedelta(days=random.randint(100, 900))
        
        for i in range(n_fraud // 4):
            dept = random.choice(officials_df[officials_df['official_id'] == collusion_official]['department'].values)
            
            transaction = {
                'transaction_id': f'TXN{str(n_normal+n_fraud//2+i+1).zfill(6)}',
                'date': base_date + timedelta(days=random.randint(0, 30)),
                'department': dept,
                'project_id': f'PRJ{random.randint(1000, 9999)}',
                'vendor_id': random.choice(collusion_vendors),
                'official_id': collusion_official,
                'amount': np.random.uniform(300000, 800000),
                'category': random.choice(self.categories),
                'payment_mode': random.choice(self.payment_modes),
                'description': 'Approved by single authority',
                'is_fraud': True,
                'fraud_type': 'collusion'
            }
            transactions.append(transaction)
        
        # Fraud Pattern 4: Spike anomaly (sudden burst of transactions)
        spike_date = self.start_date + timedelta(days=random.randint(500, 800))
        for i in range(n_fraud // 4):
            dept = random.choice(self.departments)
            baseline = dept_baselines[dept]
            
            transaction = {
                'transaction_id': f'TXN{str(n_normal+3*n_fraud//4+i+1).zfill(6)}',
                'date': spike_date + timedelta(hours=random.randint(0, 48)),
                'department': dept,
                'project_id': f'PRJ{random.randint(1000, 9999)}',
                'vendor_id': random.choice(normal_vendors['vendor_id'].values),
                'official_id': random.choice(officials_df['official_id'].values),
                'amount': baseline * random.uniform(2, 4),
                'category': random.choice(self.categories),
                'payment_mode': random.choice(self.payment_modes),
                'description': 'Emergency procurement',
                'is_fraud': True,
                'fraud_type': 'spike'
            }
            transactions.append(transaction)
        
        df = pd.DataFrame(transactions)
        df['amount'] = df['amount'].round(2)
        return df
    
    def generate_tenders(self, vendors_df, n_normal=100, n_fraud=20):
        """Generate tender documents with fraud patterns"""
        tenders = []
        
        normal_vendors = vendors_df[~vendors_df['is_fraud']]
        
        # Normal tenders
        for i in range(n_normal):
            tender = {
                'tender_id': f'TND{str(i+1).zfill(5)}',
                'title': f'{random.choice(["Construction", "Supply", "Maintenance"])} of {random.choice(["Road", "Building", "Equipment", "System"])}',
                'description': f'Detailed specifications for {random.choice(self.categories)} work including technical requirements, timelines, and quality standards.',
                'estimated_value': np.random.uniform(100000, 5000000),
                'department': random.choice(self.departments),
                'published_date': self.start_date + timedelta(days=random.randint(0, 1000)),
                'deadline': self.start_date + timedelta(days=random.randint(30, 1050)),
                'winner_vendor_id': random.choice(normal_vendors['vendor_id'].values),
                'award_amount': np.random.uniform(100000, 5000000),
                'specifications': f'Technical specification document version {random.randint(1,5)} with {random.randint(20,100)} pages of detailed requirements.',
                'is_fraud': False,
                'fraud_type': None
            }
            tenders.append(tender)
        
        # Fraud Pattern 1: Copy-paste tenders (identical descriptions)
        base_description = "Supply of equipment as per standard specifications mentioned in annexure"
        for i in range(n_fraud // 2):
            tender = {
                'tender_id': f'TND{str(n_normal+i+1).zfill(5)}',
                'title': f'{random.choice(["Supply", "Procurement"])} of Equipment',
                'description': base_description,  # Identical across multiple tenders
                'estimated_value': np.random.uniform(500000, 2000000),
                'department': random.choice(self.departments),
                'published_date': self.start_date + timedelta(days=random.randint(0, 1000)),
                'deadline': self.start_date + timedelta(days=random.randint(5, 15)),  # Unrealistic deadline
                'winner_vendor_id': random.choice(normal_vendors['vendor_id'].values),
                'award_amount': np.random.uniform(500000, 2000000),
                'specifications': 'As per requirement',  # Vague
                'is_fraud': True,
                'fraud_type': 'copy_paste'
            }
            tenders.append(tender)
        
        # Fraud Pattern 2: Vague specifications favoring specific vendor
        for i in range(n_fraud // 2):
            tender = {
                'tender_id': f'TND{str(n_normal+n_fraud//2+i+1).zfill(5)}',
                'title': 'Consulting Services',
                'description': 'Provide consulting services as needed',  # Extremely vague
                'estimated_value': np.random.uniform(1000000, 3000000),
                'department': random.choice(self.departments),
                'published_date': self.start_date + timedelta(days=random.randint(0, 1000)),
                'deadline': self.start_date + timedelta(days=random.randint(3, 7)),  # Very short
                'winner_vendor_id': random.choice(normal_vendors['vendor_id'].values),
                'award_amount': np.random.uniform(1500000, 4000000),  # Much higher than estimate
                'specifications': 'Standard requirements apply',  # Vague
                'is_fraud': True,
                'fraud_type': 'vague_spec'
            }
            tenders.append(tender)
        
        df = pd.DataFrame(tenders)
        df['estimated_value'] = df['estimated_value'].round(2)
        df['award_amount'] = df['award_amount'].round(2)
        return df
    
    def generate_citizen_feedback(self, transactions_df, n_normal=300, n_fraud=50):
        """Generate citizen complaints with fraud indicators"""
        feedback = []
        
        sentiments = ['Positive', 'Neutral', 'Negative', 'Very Negative']
        regions = ['North', 'South', 'East', 'West', 'Central']
        
        # Normal feedback
        for i in range(n_normal):
            proj_id = random.choice(transactions_df['project_id'].values)
            dept = transactions_df[transactions_df['project_id'] == proj_id]['department'].values[0]
            
            sentiment = random.choice(sentiments)
            
            if sentiment == 'Positive':
                text = random.choice([
                    'Good quality work completed on time',
                    'Satisfied with the project outcome',
                    'Infrastructure improved significantly'
                ])
            else:
                text = random.choice([
                    'Some delays observed',
                    'Quality could be better',
                    'Minor issues with execution'
                ])
            
            fb = {
                'feedback_id': f'FB{str(i+1).zfill(5)}',
                'date': self.start_date + timedelta(days=random.randint(0, 1095)),
                'department': dept,
                'project_id': proj_id,
                'sentiment': sentiment,
                'complaint_text': text,
                'severity': random.randint(1, 5),
                'region': random.choice(regions),
                'is_fraud_indicator': False
            }
            feedback.append(fb)
        
        # Fraud indicators: High spending + negative feedback
        fraud_txns = transactions_df[transactions_df['is_fraud'] == True]
        for i in range(n_fraud):
            if len(fraud_txns) == 0:
                break
            
            fraud_txn = fraud_txns.sample(1).iloc[0]
            
            fb = {
                'feedback_id': f'FB{str(n_normal+i+1).zfill(5)}',
                'date': fraud_txn['date'] + timedelta(days=random.randint(30, 180)),
                'department': fraud_txn['department'],
                'project_id': fraud_txn['project_id'],
                'sentiment': random.choice(['Negative', 'Very Negative']),
                'complaint_text': random.choice([
                    'Project not completed despite payment',
                    'Poor quality materials used',
                    'No visible progress on ground',
                    'Funds misused, work not done',
                    'Contractor disappeared after payment'
                ]),
                'severity': random.randint(7, 10),
                'region': random.choice(regions),
                'is_fraud_indicator': True
            }
            feedback.append(fb)
        
        return pd.DataFrame(feedback)
    
    def generate_all(self):
        """Generate complete dataset"""
        print("Generating vendors...")
        vendors = self.generate_vendors()
        
        print("Generating officials...")
        officials = self.generate_officials()
        
        print("Generating transactions...")
        transactions = self.generate_transactions(vendors, officials)
        
        print("Generating tenders...")
        tenders = self.generate_tenders(vendors)
        
        print("Generating citizen feedback...")
        feedback = self.generate_citizen_feedback(transactions)
        
        return {
            'vendors': vendors,
            'officials': officials,
            'transactions': transactions,
            'tenders': tenders,
            'feedback': feedback
        }

if __name__ == '__main__':
    generator = DataGenerator()
    datasets = generator.generate_all()
    
    # Save to CSV
    for name, df in datasets.items():
        df.to_csv(f'{name}.csv', index=False)
        print(f"Saved {name}.csv with {len(df)} records")
