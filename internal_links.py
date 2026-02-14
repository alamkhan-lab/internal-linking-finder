import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="Internal Link Finder", layout="wide")

st.title("🔗 Internal Link Opportunity Finder")
st.write("Find pages on your site that mention a keyword but aren't linking to your target page yet.")

# 1. Inputs
col1, col2 = st.columns(2)
with col1:
    target_url = st.text_input("New Page URL (Target):", placeholder="https://mysite.com/new-post")
with col2:
    keyword = st.text_input("Target Keyword:", placeholder="e.g. 'SEO Strategy'")

sitemap_url = st.text_input("Your Sitemap URL:", placeholder="https://mysite.com/sitemap.xml")

if st.button("Find Opportunities"):
    if not target_url or not keyword or not sitemap_url:
        st.error("Please fill in all fields.")
    else:
        with st.spinner("Analyzing your site..."):
            try:
                # 2. Get URLs from Sitemap (Simplified)
                response = requests.get(sitemap_url)
                soup = BeautifulSoup(response.content, 'xml')
                urls = [loc.text for loc in soup.find_all('loc')][:20] # Limiting to 20 for speed testing
                
                opportunities = []
                
                for url in urls:
                    if url == target_url:
                        continue
                        
                    res = requests.get(url)
                    page_soup = BeautifulSoup(res.text, 'html.parser')
                    text = page_soup.get_text().lower()
                    
                    # 3. Logic: Does the keyword exist? 
                    if keyword.lower() in text:
                        # Does it already link to our target URL?
                        links = [a['href'] for a in page_soup.find_all('a', href=True)]
                        if target_url not in links:
                            opportunities.append(url)
                
                # 4. Results
                if opportunities:
                    st.success(f"Found {len(opportunities)} link opportunities!")
                    st.write(opportunities)
                else:
                    st.warning("No unlinked mentions found.")
                    
            except Exception as e:
                st.error(f"Error: {e}")