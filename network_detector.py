"""
JANUS-AI: Module 3 - Network & Collusion Detection
Uses graph analysis to detect suspicious relationships and collusion patterns
"""

import pandas as pd
import numpy as np
import networkx as nx
from collections import defaultdict, Counter
import warnings
warnings.filterwarnings('ignore')

class NetworkCollusionDetector:
    def __init__(self):
        self.graph = nx.Graph()
        self.vendor_official_edges = defaultdict(int)
        self.suspicious_communities = []
        
    def build_transaction_network(self, transactions_df, vendors_df):
        """Build bipartite graph connecting vendors, officials, and transactions"""
        print("Building transaction network...")
        
        # Add nodes
        for _, row in vendors_df.iterrows():
            self.graph.add_node(
                row['vendor_id'],
                node_type='vendor',
                name=row['vendor_name'],
                is_fraud=row['is_fraud']
            )
        
        officials = transactions_df['official_id'].unique()
        for official_id in officials:
            self.graph.add_node(
                official_id,
                node_type='official'
            )
        
        # Add edges (vendor-official connections via transactions)
        for _, txn in transactions_df.iterrows():
            vendor = txn['vendor_id']
            official = txn['official_id']
            amount = txn['amount']
            
            if self.graph.has_edge(vendor, official):
                # Increase weight for repeated connections
                self.graph[vendor][official]['weight'] += 1
                self.graph[vendor][official]['total_amount'] += amount
                self.graph[vendor][official]['transactions'].append(txn['transaction_id'])
            else:
                self.graph.add_edge(
                    vendor,
                    official,
                    weight=1,
                    total_amount=amount,
                    transactions=[txn['transaction_id']]
                )
            
            # Track edge frequency
            self.vendor_official_edges[(vendor, official)] += 1
        
        print(f"Network built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        
    def detect_repeated_interactions(self, threshold=5):
        """Find vendor-official pairs with suspiciously high interaction frequency"""
        suspicious_pairs = []
        
        for (vendor, official), count in self.vendor_official_edges.items():
            if count >= threshold:
                edge_data = self.graph[vendor][official]
                suspicious_pairs.append({
                    'vendor_id': vendor,
                    'official_id': official,
                    'interaction_count': count,
                    'total_amount': edge_data['total_amount'],
                    'avg_transaction': edge_data['total_amount'] / count,
                    'risk_score': min(100, count * 10)  # Higher frequency = higher risk
                })
        
        return pd.DataFrame(suspicious_pairs).sort_values('risk_score', ascending=False)
    
    def detect_hub_officials(self, threshold=10):
        """Identify officials connected to unusually many vendors"""
        hub_officials = []
        
        for node in self.graph.nodes():
            if self.graph.nodes[node].get('node_type') == 'official':
                degree = self.graph.degree(node)
                
                if degree >= threshold:
                    # Calculate total money flow
                    total_flow = sum(
                        self.graph[node][neighbor]['total_amount']
                        for neighbor in self.graph.neighbors(node)
                    )
                    
                    hub_officials.append({
                        'official_id': node,
                        'vendor_connections': degree,
                        'total_amount_approved': total_flow,
                        'risk_score': min(100, degree * 5)
                    })
        
        return pd.DataFrame(hub_officials).sort_values('risk_score', ascending=False)
    
    def detect_vendor_clusters(self):
        """Find clusters of vendors connected to same officials (potential shell companies)"""
        # Get vendor subgraph (vendors connected through common officials)
        vendor_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n].get('node_type') == 'vendor']
        
        # Create vendor-vendor connections through shared officials
        vendor_graph = nx.Graph()
        
        for v1 in vendor_nodes:
            v1_officials = set(self.graph.neighbors(v1))
            
            for v2 in vendor_nodes:
                if v1 >= v2:  # Avoid duplicates
                    continue
                
                v2_officials = set(self.graph.neighbors(v2))
                shared_officials = v1_officials & v2_officials
                
                if len(shared_officials) >= 2:  # At least 2 shared officials
                    vendor_graph.add_edge(v1, v2, shared_officials=len(shared_officials))
        
        # Find connected components (clusters)
        clusters = list(nx.connected_components(vendor_graph))
        
        suspicious_clusters = []
        for cluster in clusters:
            if len(cluster) >= 3:  # At least 3 vendors in cluster
                cluster_officials = set()
                cluster_amount = 0
                
                for vendor in cluster:
                    for official in self.graph.neighbors(vendor):
                        cluster_officials.add(official)
                        cluster_amount += self.graph[vendor][official]['total_amount']
                
                suspicious_clusters.append({
                    'cluster_id': f'CLUSTER_{len(suspicious_clusters)+1}',
                    'vendors': list(cluster),
                    'vendor_count': len(cluster),
                    'shared_officials': list(cluster_officials),
                    'official_count': len(cluster_officials),
                    'total_amount': cluster_amount,
                    'risk_score': min(100, len(cluster) * 15)
                })
        
        return pd.DataFrame(suspicious_clusters).sort_values('risk_score', ascending=False)
    
    def detect_circular_patterns(self, transactions_df):
        """Detect circular money flow patterns (A->B->C->A)"""
        circular_patterns = []
        
        # Look for simple cycles in directed graph
        directed_graph = nx.DiGraph()
        
        for _, txn in transactions_df.iterrows():
            directed_graph.add_edge(
                txn['official_id'],
                txn['vendor_id'],
                amount=txn['amount'],
                transaction_id=txn['transaction_id']
            )
        
        # Find cycles
        try:
            cycles = list(nx.simple_cycles(directed_graph))
            for cycle in cycles:
                if len(cycle) >= 3:  # At least 3 nodes in cycle
                    cycle_amount = 0
                    for i in range(len(cycle)):
                        src = cycle[i]
                        dst = cycle[(i+1) % len(cycle)]
                        if directed_graph.has_edge(src, dst):
                            cycle_amount += directed_graph[src][dst]['amount']
                    
                    circular_patterns.append({
                        'cycle': ' -> '.join(cycle),
                        'cycle_length': len(cycle),
                        'total_flow': cycle_amount,
                        'risk_score': len(cycle) * 20
                    })
        except:
            pass  # No cycles found
        
        return pd.DataFrame(circular_patterns)
    
    def compute_centrality_scores(self):
        """Compute centrality metrics to identify key players"""
        # Betweenness centrality (brokers)
        betweenness = nx.betweenness_centrality(self.graph, weight='weight')
        
        # Degree centrality (connectivity)
        degree_centrality = nx.degree_centrality(self.graph)
        
        # PageRank (influence)
        pagerank = nx.pagerank(self.graph, weight='weight')
        
        centrality_scores = []
        for node in self.graph.nodes():
            centrality_scores.append({
                'node_id': node,
                'node_type': self.graph.nodes[node].get('node_type'),
                'betweenness': betweenness.get(node, 0),
                'degree_centrality': degree_centrality.get(node, 0),
                'pagerank': pagerank.get(node, 0),
                'centrality_risk_score': (
                    betweenness.get(node, 0) * 100 +
                    pagerank.get(node, 0) * 100
                ) / 2
            })
        
        return pd.DataFrame(centrality_scores).sort_values('centrality_risk_score', ascending=False)
    
    def aggregate_network_scores(self, transactions_df):
        """Aggregate network signals for each transaction"""
        # Get all network analyses
        repeated_pairs = self.detect_repeated_interactions()
        hub_officials = self.detect_hub_officials()
        clusters = self.detect_vendor_clusters()
        
        # Create transaction-level scores
        results = transactions_df[['transaction_id', 'vendor_id', 'official_id', 'amount']].copy()
        results['network_anomaly_score'] = 0
        
        # Score based on repeated interactions
        if len(repeated_pairs) > 0:
            suspicious_edges = set(zip(repeated_pairs['vendor_id'], repeated_pairs['official_id']))
            results['is_repeated_pair'] = results.apply(
                lambda row: (row['vendor_id'], row['official_id']) in suspicious_edges,
                axis=1
            )
            results.loc[results['is_repeated_pair'], 'network_anomaly_score'] += 40
        else:
            results['is_repeated_pair'] = False
        
        # Score based on hub officials
        if len(hub_officials) > 0:
            hub_official_ids = set(hub_officials['official_id'])
            results['is_hub_official'] = results['official_id'].isin(hub_official_ids)
            results.loc[results['is_hub_official'], 'network_anomaly_score'] += 30
        else:
            results['is_hub_official'] = False
        
        # Score based on cluster membership
        if len(clusters) > 0:
            cluster_vendors = set()
            for vendors in clusters['vendors']:
                cluster_vendors.update(vendors)
            results['is_cluster_vendor'] = results['vendor_id'].isin(cluster_vendors)
            results.loc[results['is_cluster_vendor'], 'network_anomaly_score'] += 35
        else:
            results['is_cluster_vendor'] = False
        
        # Normalize
        results['network_anomaly_score'] = results['network_anomaly_score'].clip(0, 100)
        
        return results
    
    def get_top_network_anomalies(self, results, top_n=20):
        """Get most suspicious network patterns"""
        return results.nlargest(top_n, 'network_anomaly_score')

# Example usage
if __name__ == '__main__':
    # Load data
    transactions = pd.read_csv('transactions.csv')
    vendors = pd.read_csv('vendors.csv')
    
    # Initialize and run detector
    detector = NetworkCollusionDetector()
    detector.build_transaction_network(transactions, vendors)
    
    # Get analysis results
    print("\n=== REPEATED VENDOR-OFFICIAL PAIRS ===")
    repeated_pairs = detector.detect_repeated_interactions()
    print(repeated_pairs.head(10))
    
    print("\n=== HUB OFFICIALS ===")
    hub_officials = detector.detect_hub_officials()
    print(hub_officials.head(10))
    
    print("\n=== SUSPICIOUS VENDOR CLUSTERS ===")
    clusters = detector.detect_vendor_clusters()
    print(clusters.head(5))
    
    # Aggregate scores
    results = detector.aggregate_network_scores(transactions)
    
    # Get top anomalies
    top_anomalies = detector.get_top_network_anomalies(results, top_n=20)
    
    print("\n=== TOP 20 NETWORK ANOMALIES ===\n")
    for idx, row in top_anomalies.iterrows():
        print(f"Transaction: {row['transaction_id']}")
        print(f"  Network Score: {row['network_anomaly_score']:.1f}/100")
        print(f"  Vendor: {row['vendor_id']}")
        print(f"  Official: {row['official_id']}")
        print(f"  Amount: ${row['amount']:,.2f}")
        print()
    
    # Save results
    results.to_csv('network_anomalies.csv', index=False)
    repeated_pairs.to_csv('repeated_pairs.csv', index=False)
    hub_officials.to_csv('hub_officials.csv', index=False)
    clusters.to_csv('vendor_clusters.csv', index=False)
    
    print("\nNetwork analysis complete. Results saved.")
