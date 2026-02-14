import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

# --- UI CONFIG ---
st.set_page_config(page_title="SEO Link Pro: Enterprise", page_icon="🏢", layout="wide")

# --- HELPER FUNCTIONS ---
def normalize_url(url):
    if not url: return ""
    url = str(url).lower().strip().replace("https://", "").replace("http://", "")
    if url.endswith("/"): url = url[:-1]
    return url

def get_urls_from_sitemap(sitemap_url, filter_path=""):
    """Fetch URLs, handling Sitemap Indexes and filtering by path."""
    try:
        res = requests.get(sitemap_url, timeout=10)
        soup = BeautifulSoup(res.content, 'xml')
        
        # Check if it's a Sitemap Index or a standard Sitemap
        tags = soup.find_all('loc')
        urls = [t.text for t in tags]
        
        # If it's a sitemap index, we might need to go one level deeper 
        # But for speed, we will filter the current list first
        if filter_path:
            urls = [u for u in urls if filter_path in u]
            
        return list(set(urls))
    except:
        return []

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚡ Enterprise Settings")
    url_filter = st.text_input("URL Path Filter (Recommended)", placeholder="e.g. /blog/", help="Only scan URLs containing this string. Essential for sites with 100k+ pages.")
    max_pages = st.number_input("Scan Limit", min_value=10, max_value=5000, value=200, help="How many pages to check in this session.")
    st.warning("⚠️ Large sites take time. Scanning 200 pages takes ~3-5 minutes.")

# --- MAIN UI ---
st.title("🔗 Internal Link Opportunity Finder (Large Site Mode)")
st.info(f"Targeting a site with 100k+ pages? Use the **URL Path Filter** in the sidebar to focus on your blog or resource section.")

col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader("Upload CSV (Col A: Target URL, Col B: Keyword)", type="csv")
with col2:
    sitemap_input = st.text_input("Sitemap URL", placeholder="https://example.com/post-sitemap.xml")
    run_btn = st.button("🚀 Start Focused Analysis")

if run_btn and uploaded_file and sitemap_input:
    df_targets = pd.read_csv(uploaded_file)
    
    with st.status("Gathering and Filtering URLs...", expanded=True) as status:
        # Step 1: Get filtered URLs
        all_urls = get_urls_from_sitemap(sitemap_input, url_filter)
        all_urls = all_urls[:int(max_pages)] # Apply the cap
        
        if not all_urls:
            st.error("No URLs found. If this is a Sitemap Index, try pasting the specific sub-sitemap URL (e.g., sitemap-posts.xml) instead.")
            st.stop()
            
        st.write(f"✅ Found {len(all_urls)} URLs matching your filter.")
        
        results = []
        progress_bar = st.progress(0)
        
        # Step 2: Analysis Loop
        for idx, row in df_targets.iterrows():
            target_url = str(row.iloc[0]).strip()
            keyword = str(row.iloc[1]).strip().lower()
            norm_target = normalize_url(target_url)
            
            status.write(f"Searching for **'{keyword}'**...")
            
            for i, site_url in enumerate(all_urls):
                if normalize_url(site_url) == norm_target:
                    continue
                
                try:
                    # Update internal progress
                    h = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1)'}
                    r = requests.get(site_url, headers=h, timeout=5)
                    s = BeautifulSoup(r.text, 'html.parser')
                    text = s.get_text().lower()
                    
                    if keyword in text:
                        links = [normalize_url(a.get('href')) for a in s.find_all('a', href=True)]
                        if norm_target not in links:
                            results.append({"Keyword": keyword, "Found on": site_url, "Missing Link To": target_url})
                except:
                    continue
            
            progress_bar.progress((idx + 1) / len(df_targets))

        status.update(label="Analysis Complete!", state="complete")

    # Display Results
    if results:
        res_df = pd.DataFrame(results)
        st.subheader("🎯 Opportunities Found")
        st.dataframe(res_df, use_container_width=True)
        st.download_button("Download Report", res_df.to_csv(index=False), "links.csv")
    else:
        st.warning("No unlinked mentions found in the sampled pages.")
