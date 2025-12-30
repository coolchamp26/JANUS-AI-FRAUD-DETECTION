"""
JANUS-AI: Interactive Dashboard
Streamlit-based dashboard for fraud detection visualization
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import networkx as nx
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="JANUS-AI Fraud Detection System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 48px;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 20px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .critical-alert {
        background-color: #ff4b4b;
        color: white;
        padding: 15px;
        border-radius: 5px;
        font-weight: bold;
    }
    .high-alert {
        background-color: #ffa500;
        color: white;
        padding: 15px;
        border-radius: 5px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_all_data():
    """Load all datasets and normalize schema for dashboard"""
    try:
        data = {
            'meta_scores': pd.read_csv('meta_fraud_scores.csv'),
            'cases': pd.read_csv('investigation_cases.csv'),
            'transactions': pd.read_csv('transactions.csv'),
            'vendors': pd.read_csv('vendors.csv'),
            'repeated_pairs': pd.read_csv('repeated_pairs.csv'),
            'hub_officials': pd.read_csv('hub_officials.csv'),
            'vendor_clusters': pd.read_csv('vendor_clusters.csv'),
            'mismatch': pd.read_csv('spending_satisfaction_mismatch.csv')
        }

        # -------------------------------
        # 🔧 SCHEMA NORMALIZATION (CRITICAL)
        # -------------------------------
        meta = data['meta_scores']

        # Normalize vendor_id for plots & hover
        if 'vendor_id' not in meta.columns:
            if 'vendor_id_x' in meta.columns:
                meta['vendor_id'] = meta['vendor_id_x']
            elif 'vendor_id_y' in meta.columns:
                meta['vendor_id'] = meta['vendor_id_y']
            else:
                meta['vendor_id'] = 'UNKNOWN'

        data['meta_scores'] = meta

        return data

    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None


def create_risk_distribution_chart(meta_scores):
    """Create risk level distribution pie chart"""
    risk_counts = meta_scores['risk_level'].value_counts()
    
    fig = px.pie(
        values=risk_counts.values,
        names=risk_counts.index,
        title='Risk Level Distribution',
        color=risk_counts.index,
        color_discrete_map={
            'CRITICAL': '#FF0000',
            'HIGH': '#FF6B00',
            'MEDIUM': '#FFB800',
            'LOW': '#90EE90',
            'MINIMAL': '#00FF00'
        }
    )
    
    return fig

def create_department_heatmap(meta_scores):
    """Create fraud heatmap by department"""
    dept_stats = meta_scores.groupby('department').agg({
        'meta_fraud_score': 'mean',
        'transaction_id': 'count'
    }).reset_index()
    dept_stats.columns = ['Department', 'Avg Fraud Score', 'Transaction Count']
    
    fig = px.bar(
        dept_stats.sort_values('Avg Fraud Score', ascending=False),
        x='Department',
        y='Avg Fraud Score',
        color='Avg Fraud Score',
        title='Average Fraud Score by Department',
        color_continuous_scale='Reds'
    )
    
    return fig

def create_temporal_timeline(meta_scores):
    """Create temporal anomaly timeline"""
    meta_scores['date'] = pd.to_datetime(meta_scores['date'])
    meta_scores['month'] = meta_scores['date'].dt.to_period('M').astype(str)
    
    monthly_risk = meta_scores.groupby('month').agg({
        'meta_fraud_score': 'mean',
        'transaction_id': 'count'
    }).reset_index()
    monthly_risk.columns = ['Month', 'Avg Risk Score', 'Transaction Count']
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=monthly_risk['Month'],
        y=monthly_risk['Avg Risk Score'],
        mode='lines+markers',
        name='Avg Risk Score',
        line=dict(color='red', width=3)
    ))
    
    fig.update_layout(
        title='Fraud Risk Trend Over Time',
        xaxis_title='Month',
        yaxis_title='Average Fraud Score'
    )
    
    return fig

def create_amount_vs_risk_scatter(meta_scores):
    """Create scatter plot of amount vs risk"""
    sample = meta_scores.sample(min(500, len(meta_scores)))
    
    fig = px.scatter(
        sample,
        x='amount',
        y='meta_fraud_score',
        color='risk_level',
        size='amount',
        hover_data=['department', 'vendor_id'],
        title='Transaction Amount vs Fraud Risk',
        color_discrete_map={
            'CRITICAL': '#FF0000',
            'HIGH': '#FF6B00',
            'MEDIUM': '#FFB800',
            'LOW': '#90EE90',
            'MINIMAL': '#00FF00'
        }
    )
    
    fig.update_xaxes(title='Transaction Amount ($)', type='log')
    fig.update_yaxes(title='Fraud Risk Score')
    
    return fig

def create_network_visualization(repeated_pairs):
    """Create network graph of suspicious connections"""
    # Sample top connections
    top_pairs = repeated_pairs.nlargest(20, 'risk_score')
    
    # Create network graph
    G = nx.Graph()
    
    for _, row in top_pairs.iterrows():
        G.add_edge(
            row['vendor_id'],
            row['official_id'],
            weight=row['interaction_count']
        )
    
    pos = nx.spring_layout(G, seed=42)
    
    edge_trace = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace.append(
            go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode='lines',
                line=dict(width=2, color='#888'),
                hoverinfo='none'
            )
        )
    
    node_trace = go.Scatter(
        x=[],
        y=[],
        text=[],
        mode='markers+text',
        hoverinfo='text',
        marker=dict(
            size=20,
            color=[],
            line_width=2
        )
    )
    
    for node in G.nodes():
        x, y = pos[node]
        node_trace['x'] += tuple([x])
        node_trace['y'] += tuple([y])
        node_trace['text'] += tuple([node])
        node_trace['marker']['color'] += tuple(['red' if 'VEN' in node else 'blue'])
    
    fig = go.Figure(data=edge_trace + [node_trace])
    
    fig.update_layout(
        title='Collusion Network (Top 20 Suspicious Connections)',
        showlegend=False,
        hovermode='closest',
        margin=dict(b=0,l=0,r=0,t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )
    
    return fig

def main():
    # Header
    st.markdown('<div class="main-header">🔍 JANUS-AI</div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 18px;">AI-Powered Public Fraud & Anomaly Detection System</p>', unsafe_allow_html=True)
    
    # Load data
    data = load_all_data()
    
    if data is None:
        st.error("Failed to load data. Please ensure all CSV files are present.")
        return
    
    meta_scores = data['meta_scores']
    cases = data['cases']
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select View",
        ["Dashboard Overview", "Investigation Cases", "Network Analysis", "Detailed Analytics"]
    )
    
    # Calculate statistics
    total_txns = len(meta_scores)
    critical_count = len(meta_scores[meta_scores['risk_level'] == 'CRITICAL'])
    high_count = len(meta_scores[meta_scores['risk_level'] == 'HIGH'])
    flagged_amount = meta_scores[meta_scores['meta_fraud_score'] > 50]['amount'].sum()
    total_amount = meta_scores['amount'].sum()
    
    # Dashboard Overview
    if page == "Dashboard Overview":
        st.header("📊 Executive Dashboard")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Transactions",
                f"{total_txns:,}",
                delta=None
            )
        
        with col2:
            st.metric(
                "Critical Risks",
                f"{critical_count:,}",
                delta=f"{critical_count/total_txns*100:.1f}%",
                delta_color="inverse"
            )
        
        with col3:
            st.metric(
                "High Risks",
                f"{high_count:,}",
                delta=f"{high_count/total_txns*100:.1f}%",
                delta_color="inverse"
            )
        
        with col4:
            st.metric(
                "Flagged Amount",
                f"${flagged_amount/1e6:.1f}M",
                delta=f"{flagged_amount/total_amount*100:.1f}% of total",
                delta_color="inverse"
            )
        
        st.markdown("---")
        
        # Charts row 1
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = create_risk_distribution_chart(meta_scores)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            fig2 = create_department_heatmap(meta_scores)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Charts row 2
        col1, col2 = st.columns(2)
        
        with col1:
            fig3 = create_temporal_timeline(meta_scores)
            st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            fig4 = create_amount_vs_risk_scatter(meta_scores)
            st.plotly_chart(fig4, use_container_width=True)
    
    # Investigation Cases
    elif page == "Investigation Cases":
        st.header("🔎 Priority Investigation Cases")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            risk_filter = st.multiselect(
                "Risk Level",
                options=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
                default=['CRITICAL', 'HIGH']
            )
        
        with col2:
            dept_filter = st.multiselect(
                "Department",
                options=sorted(cases['department'].unique()),
                default=None
            )
        
        with col3:
            min_amount = st.number_input(
                "Minimum Amount ($)",
                min_value=0,
                value=0,
                step=10000
            )
        
        # Filter cases
        filtered_cases = cases[cases['risk_level'].isin(risk_filter)]
        if dept_filter:
            filtered_cases = filtered_cases[filtered_cases['department'].isin(dept_filter)]
        filtered_cases = filtered_cases[filtered_cases['amount'] >= min_amount]
        
        st.write(f"Showing {len(filtered_cases)} cases")
        
        # Display cases
        for idx, case in filtered_cases.head(20).iterrows():
            with st.expander(f"**{case['case_id']}** - {case['transaction_id']} | Risk: {case['risk_level']} | Score: {case['meta_fraud_score']:.1f}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Amount:** ${case['amount']:,.2f}")
                    st.write(f"**Department:** {case['department']}")
                    st.write(f"**Date:** {case['date']}")
                
                with col2:
                    st.write(f"**Vendor:** {case['vendor_id']}")
                    st.write(f"**Official:** {case['official_id']}")
                    st.write(f"**Modules Flagged:** {case['num_modules_flagged']}")
                
                st.write(f"**Detection Modules:** {case['flagged_modules']}")
                
                if st.button(f"Generate Full Report", key=case['case_id']):
                    st.info("Full explainability report would be generated here using explainability_engine.py")
    
    # Network Analysis
    elif page == "Network Analysis":
        st.header("🕸️ Network & Collusion Analysis")
        
        tab1, tab2, tab3 = st.tabs(["Collusion Network", "Hub Officials", "Vendor Clusters"])
        
        with tab1:
            st.subheader("Suspicious Vendor-Official Connections")
            fig = create_network_visualization(data['repeated_pairs'])
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(
                data['repeated_pairs'].nlargest(10, 'risk_score'),
                use_container_width=True
            )
        
        with tab2:
            st.subheader("Officials Connected to Many Vendors")
            st.dataframe(
                data['hub_officials'].nlargest(10, 'risk_score'),
                use_container_width=True
            )
        
        with tab3:
            st.subheader("Suspicious Vendor Clusters")
            st.dataframe(
                data['vendor_clusters'].nlargest(5, 'risk_score'),
                use_container_width=True
            )
    
    # Detailed Analytics
    elif page == "Detailed Analytics":
        st.header("📈 Detailed Analytics")
        
        # Module-wise score distribution
        st.subheader("Module-Wise Score Distribution")
        
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=('Financial', 'Temporal', 'Network', 'NLP', 'Citizen Feedback', 'Meta Score')
        )
        
        scores = ['financial_score', 'temporal_anomaly_score', 'network_anomaly_score', 
                  'nlp_anomaly_score', 'citizen_feedback_score', 'meta_fraud_score']
        
        positions = [(1,1), (1,2), (1,3), (2,1), (2,2), (2,3)]
        
        for score, pos in zip(scores, positions):
            fig.add_trace(
                go.Histogram(x=meta_scores[score], name=score, nbinsx=30),
                row=pos[0], col=pos[1]
            )
        
        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Correlation analysis
        st.subheader("Score Correlation Matrix")
        corr_data = meta_scores[scores].corr()
        
        fig = px.imshow(
            corr_data,
            text_auto='.2f',
            aspect='auto',
            color_continuous_scale='RdBu_r',
            title='Module Score Correlations'
        )
        st.plotly_chart(fig, use_container_width=True)

if __name__ == '__main__':
    main()
