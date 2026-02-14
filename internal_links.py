import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

# --- UI CONFIG ---
st.set_page_config(page_title="SEO Link Pro: Cloudflare Edition", page_icon="🔗", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #31333f; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF4B4B; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def normalize_url(url):
    if not url: return ""
    url = str(url).lower().strip().replace("https://", "").replace("http://", "")
    if url.endswith("/"): url = url[:-1]
    return url

def fetch_page_content(url):
    """Fetch HTML using Googlebot headers (Usually bypasses page blocks)."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.text
        else:
            return f"ERROR:{r.status_code}"
    except Exception as e:
        return f"ERROR:{str(e)}"

# --- SIDEBAR ---
with st.sidebar:
    st.header("💡 Pro Tip")
    st.write("""
    Since Cloudflare blocks automated sitemap fetching, 
    please paste the list of URLs you want to scan directly.
    You can get these from your browser or Screaming Frog.
    """)
    st.markdown("---")
    st.caption("v2.1 - Cloudflare Bypass Mode")

# --- MAIN UI ---
st.title("🔗 Internal Link Opportunity Finder")
st.info("Direct Scan Mode: Paste URLs to bypass Sitemap blocks.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Step 1: Upload Targets")
    uploaded_targets = st.file_uploader("Upload Target CSV (Col A: URL, Col B: Keyword)", type="csv")
    if uploaded_targets:
        df_targets = pd.read_csv(uploaded_targets)
        st.success(f"Loaded {len(df_targets)} keywords.")

with col2:
    st.subheader("Step 2: URLs to Scan")
    urls_to_scan_input = st.text_area("Paste URLs to scan (one per line)", height=150, placeholder="https://example.com/page-1\nhttps://example.com/page-2")
    
    st.write("--- OR ---")
    
    uploaded_scan_list = st.file_uploader("Upload CSV of URLs to scan", type="csv")

run_analysis = st.button("🚀 Start Focused Analysis")

# --- ANALYSIS LOGIC ---
if run_analysis and uploaded_targets:
    # Prepare URL List
    all_site_urls = []
    if urls_to_scan_input:
        all_site_urls = [u.strip() for u in urls_to_scan_input.split('\n') if u.strip()]
    elif uploaded_scan_list:
        scan_df = pd.read_csv(uploaded_scan_list)
        all_site_urls = scan_df.iloc[:, 0].tolist()

    if not all_site_urls:
        st.error("Please provide at least one URL to scan.")
        st.stop()

    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    with st.status("Analyzing Pages...", expanded=True) as status:
        for idx, row in df_targets.iterrows():
            target_url = str(row.iloc[0]).strip()
            keyword = str(row.iloc[1]).strip().lower()
            norm_target = normalize_url(target_url)
            
            status.write(f"Searching for: **{keyword}**")
            
            for site_url in all_site_urls:
                if normalize_url(site_url) == norm_target:
                    continue
                
                html = fetch_page_content(site_url)
                
                if html and html.startswith("ERROR:"):
                    status.write(f"❌ Could not read {site_url} (Code {html.split(':')[1]})")
                    continue
                
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    # Clean text
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    full_text = soup.get_text().lower()
                    
                    if keyword in full_text:
                        links = [normalize_url(a.get('href')) for a in soup.find_all('a', href=True)]
                        if norm_target not in links:
                            results.append({
                                "Keyword": keyword,
                                "Found on Page": site_url,
                                "Missing Link to": target_url
                            })
            
            progress_bar.progress((idx + 1) / len(df_targets))
        
        status.update(label="Analysis Complete!", state="complete", expanded=False)

    # --- DISPLAY RESULTS ---
    if results:
        res_df = pd.DataFrame(results)
        st.subheader("🎯 Link Opportunities Found")
        st.dataframe(res_df, use_container_width=True)
        st.download_button("📩 Download CSV Report", res_df.to_csv(index=False), "link_gaps.csv")
    else:
        st.warning("No unlinked mentions found. If you see '❌ Could not read' errors above, the site is blocking the scan.")
