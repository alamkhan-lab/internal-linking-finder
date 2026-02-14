import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

# --- 1. UI CONFIGURATION ---
st.set_page_config(page_title="SEO Link Pro: Enterprise", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #31333f; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF4B4B; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HELPER FUNCTIONS ---

def normalize_url(url):
    """Clean URLs for accurate comparison."""
    if not url: return ""
    url = str(url).lower().strip().replace("https://", "").replace("http://", "")
    if url.endswith("/"): url = url[:-1]
    return url

def get_urls_from_sitemap(sitemap_url, filter_path=""):
    """Fetch URLs with Browser Headers to bypass Shopify/Cloudflare security."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        res = requests.get(sitemap_url, headers=headers, timeout=20)
        
        if res.status_code != 200:
            st.error(f"⚠️ Access Denied (Status {res.status_code}). Shopify/Cloudflare is blocking the request. Try a different sub-sitemap URL.")
            return []

        # Parse XML (Using 'xml' features)
        soup = BeautifulSoup(res.content, 'xml')
        tags = soup.find_all('loc')
        urls = [t.text.strip() for t in tags]
        
        # Filter URLs based on user input (e.g., /collections/)
        if filter_path:
            urls = [u for u in urls if filter_path in u]
            
        return list(set(urls))
    except Exception as e:
        st.error(f"Error fetching sitemap: {e}")
        return []

def fetch_page_content(url):
    """Fetch HTML with Googlebot headers (often allowed by Shopify)."""
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.text
    except:
        return None
    return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚡ Enterprise Settings")
    url_filter = st.text_input("URL Path Filter", value="/collections/", help="Only scan URLs containing this string.")
    scan_limit = st.number_input("Scan Limit (Pages)", min_value=10, max_value=5000, value=200)
    st.markdown("---")
    st.info("Tip: For Shopify sites, using '/collections/' or '/products/' helps narrow down the crawl.")

# --- 4. MAIN INTERFACE ---
st.title("🔗 Internal Link Opportunity Finder")
st.subheader("Enterprise & Large Site Mode")

col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader("Upload CSV (Col A: Target URL, Col B: Keyword)", type="csv")
    if uploaded_file:
        df_targets = pd.read_csv(uploaded_file)
        st.success(f"Loaded {len(df_targets)} target keywords.")

with col2:
    sitemap_input = st.text_input("Sitemap URL", value="https://sa.redtagfashion.com/sitemap_collections_1.xml")
    run_analysis = st.button("🚀 Start Focused Analysis")

# --- 5. ANALYSIS LOGIC ---
if run_analysis and uploaded_file and sitemap_input:
    # 1. Gather URLs
    with st.status("Accessing Sitemap...", expanded=True) as status:
        all_site_urls = get_urls_from_sitemap(sitemap_input, url_filter)
        all_site_urls = all_site_urls[:int(scan_limit)]
        
        if not all_site_urls:
            status.update(label="No URLs Found", state="error")
            st.stop()
            
        st.write(f"✅ Found {len(all_site_urls)} URLs matching your filter.")
        
        results = []
        progress_bar = st.progress(0)
        
        # 2. Loop through CSV Targets
        for idx, row in df_targets.iterrows():
            target_url = str(row.iloc[0]).strip()
            keyword = str(row.iloc[1]).strip().lower()
            norm_target = normalize_url(target_url)
            
            status.write(f"Checking mentions for: **{keyword}**")
            
            # 3. Loop through Sitemap URLs
            for site_url in all_site_urls:
                if normalize_url(site_url) == norm_target:
                    continue
                
                html = fetch_page_content(site_url)
                if not html:
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                # Remove scripts and styles from text comparison
                for script in soup(["script", "style"]):
                    script.decompose()
                
                full_text = soup.get_text().lower()
                
                if keyword in full_text:
                    # Check if target link already exists
                    links = [normalize_url(a.get('href')) for a in soup.find_all('a', href=True)]
                    if norm_target not in links:
                        results.append({
                            "Keyword": keyword,
                            "Found on Page": site_url,
                            "Missing Link to": target_url
                        })
            
            progress_bar.progress((idx + 1) / len(df_targets))
        
        status.update(label="Analysis Complete!", state="complete", expanded=False)

    # --- 6. DISPLAY RESULTS ---
    if results:
        res_df = pd.DataFrame(results)
        st.subheader("🎯 Link Opportunities Found")
        
        m1, m2 = st.columns(2)
        m1.metric("Total Gaps", len(res_df))
        m2.metric("Unique Pages", res_df['Found on Page'].nunique())
        
        st.dataframe(res_df, use_container_width=True)
        st.download_button("📩 Download CSV Report", res_df.to_csv(index=False), "seo_link_gaps.csv")
    else:
        st.warning("No unlinked mentions found in the pages scanned. Try increasing the scan limit or changing the path filter.")
