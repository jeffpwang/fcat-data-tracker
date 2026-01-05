import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import networkx as nx

def render_data_inspector(df: pd.DataFrame):
    """
    Shows a high-level summary of the dataset 'Health'.
    """
    st.divider()
    st.subheader("🔍 Data Profile")
    
    # 1. High-Level Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", len(df))
    c2.metric("Columns", len(df.columns))
    
    # Count missing values
    missing_count = df.isnull().sum().sum()
    c3.metric("Missing Values", missing_count)
    
    # Detect 'Value' column for volatility check
    if 'value' in df.columns and pd.api.types.is_numeric_dtype(df['value']):
        volatility = df['value'].std()
        c4.metric("Volatility (Std Dev)", f"{volatility:.2f}")
    else:
        c4.metric("Volatility", "N/A")

    # 2. Tabs for Details
    tab1, tab2 = st.tabs(["📋 Raw Data Sample", "ℹ️ Column Types"])
    
    with tab1:
        st.dataframe(df.head(50), use_container_width=True)
        
    with tab2:
        # distinct_count = df.nunique()
        types = df.dtypes.astype(str)
        info_df = pd.DataFrame({"Type": types})
        st.dataframe(info_df.transpose(), use_container_width=True)

def render_completeness(df: pd.DataFrame):
    """
    A transparent 'Checklist' showing exactly WHY data passed or failed.
    """
    st.divider()
    st.subheader("✅ Completeness Scorecard")
    
    # Define what we are looking for
    dimensions = {
        "Temporal": ["date", "year", "time", "timestamp", "period"],
        "Geospatial": ["iso", "country", "region", "lat", "lon", "source", "target"],
        "Quantitative": ["value", "price", "count", "score", "index", "gdp"],
        "Relational": ["source", "target", "from", "to", "partner"]
    }
    
    c1, c2, c3, c4 = st.columns(4)
    cols = [c1, c2, c3, c4]
    
    # Check each dimension
    for i, (dim, keywords) in enumerate(dimensions.items()):
        # Find intersection between DataFrame columns and our keywords
        found = [col for col in df.columns if col.lower() in keywords]
        
        with cols[i]:
            if found:
                st.success(f"**{dim}**")
                st.caption(f"Detected: `{found[0]}`")
            else:
                st.error(f"**{dim}**")
                st.caption("Not Found")

def render_visual_potential(df: pd.DataFrame, label: str):
    """
    Smart Visualizer with FALLBACKS. 
    It tries Network -> Map -> Line -> Bar -> Histogram.
    """
    st.divider()
    st.subheader("🎨 Visual Potential")

    # Detect Shapes
    has_net = 'source' in df.columns and 'target' in df.columns
    has_geo = ('iso' in df.columns or 'country' in df.columns or 'lat' in df.columns)
    has_time = 'date' in df.columns
    has_val = 'value' in df.columns

    # --- VISUALIZATION LOGIC ---

    # 1. NETWORK (Top Priority - Rare & Valuable)
    if has_net:
        st.info("🕸️ **Network Topology Detected** (Source/Target columns found)")
        try:
            # Limit to top 50 links to prevent browser crash
            top_links = df.head(50)
            if has_val:
                top_links = df.sort_values('value', ascending=False).head(50)
            
            G = nx.from_pandas_edgelist(top_links, 'source', 'target')
            pos = nx.spring_layout(G, seed=42)
            
            # Draw with Plotly
            edge_x, edge_y = [], []
            for edge in G.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

            edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.5, color='#888'), hoverinfo='none', mode='lines')

            node_x, node_y = [], []
            node_text = []
            for node in G.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                node_text.append(str(node))

            node_trace = go.Scatter(x=node_x, y=node_y, mode='markers', hoverinfo='text', hovertext=node_text, marker=dict(size=10, color='LightSkyBlue'))

            fig = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(showlegend=False, margin=dict(b=0,l=0,r=0,t=0), xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))
            st.plotly_chart(fig, use_container_width=True)
            return # Stop here if network found
        except Exception as e:
            st.warning(f"Could not render Network: {e}")

    # 2. GEOSPATIAL (Map)
    if has_geo and has_val:
        st.info("🌍 **Geospatial Data Detected** (Country/ISO columns found)")
        try:
            # Heuristic: Is it points (lat/lon) or regions (iso)?
            if 'lat' in df.columns:
                st.map(df) # Simple dot map
            else:
                # Choropleth attempt (Generic World Map)
                geo_col = 'iso' if 'iso' in df.columns else 'country'
                fig = px.choropleth(df, locations=geo_col, locationmode="country names", color='value', title=f"Global Heatmap: {label}")
                st.plotly_chart(fig, use_container_width=True)
            return
        except Exception as e:
            st.warning(f"Could not render Map: {e}")

    # 3. TIME SERIES (Line Chart)
    if has_time and has_val:
        st.info("📈 **Time-Series Detected** (Date column found)")
        try:
            # Check if there are multiple categories (e.g. Multiple countries over time)
            if 'source' in df.columns:
                fig = px.line(df, x='date', y='value', color='source', title=f"Trend: {label}")
            else:
                fig = px.line(df, x='date', y='value', title=f"Trend: {label}")
            
            st.plotly_chart(fig, use_container_width=True)
            return
        except Exception as e:
            st.warning(f"Could not render Time Series: {e}")

    # 4. CATEGORICAL (Bar Chart - The "Universal Fallback")
    # If we have labels and numbers, but no dates/maps, show a Bar Chart.
    if has_val:
        st.info("📊 **Categorical Data Detected** (Values found)")
        try:
            # Try to find a text column to use as labels
            text_cols = df.select_dtypes(include=['object']).columns
            if len(text_cols) > 0:
                label_col = text_cols[0] # Pick the first text column (e.g., "Industry", "Sector")
                
                # Show Top 20 items
                top_items = df.sort_values('value', ascending=False).head(20)
                fig = px.bar(top_items, x=label_col, y='value', title=f"Top 20 Breakdown: {label}")
                st.plotly_chart(fig, use_container_width=True)
            else:
                # 5. HISTOGRAM (The "Last Resort")
                # If we only have numbers and nothing else
                st.info("🔢 **Distribution Detected** (Only values found)")
                fig = px.histogram(df, x='value', title="Data Distribution")
                st.plotly_chart(fig, use_container_width=True)
        except:
            st.warning("Could not render Bar/Hist chart.")
    
    else:
        st.warning("⚠️ No 'Value' column found. Cannot generate charts.")