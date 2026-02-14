import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re

# --- 1. UI CONFIGURATION ---
st.set_page_config(page_title="SEO Internal Link Pro", page_icon="🔗", layout="wide")

# Custom CSS for a Premium Branding
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #31333f; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF4B4B; color: white; font-weight: bold; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HELPER FUNCTIONS ---

def normalize_url(url):
    """Removes protocol and trailing slashes for accurate comparison."""
    if not url: return ""
    url = url.lower().strip().replace("https://", "").replace("http://", "")
    if url.endswith("/"): url = url[:-1]
    return url

def fetch_content(url):
    """Fetches page content using a Googlebot User-Agent."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        return None
    return None

# --- 3. SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Configuration")
    max_pages = st.slider("Sitemap Scan Limit", 10, 1000, 100, help="How many pages from the sitemap should we check?")
    debug_mode = st.checkbox("Enable Debug Mode", help="Shows what the script 'sees' on each page.")
    st.markdown("---")
    st.markdown("### How to use:")
    st.write("1. Upload CSV (Col A: Target URL, Col B: Keyword)")
    st.write("2. Enter Sitemap URL")
    st.write("3. Run Analysis")

# --- 4. MAIN INTERFACE ---
st.title("🔗 Internal Link Opportunity Finder")
st.write("Find 'unlinked mentions' of your target keywords across your website.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Step 1: Upload Targets")
    uploaded_file = st.file_uploader("Upload CSV File", type="csv")
    if uploaded_file:
        df_targets = pd.read_csv(uploaded_file)
        st.success(f"✅ {len(df_targets)} targets loaded.")

with col2:
    st.subheader("Step 2: Site Source")
    sitemap_url = st.text_input("Enter Sitemap XML URL", placeholder="https://example.com/sitemap.xml")
    run_analysis = st.button("🚀 Run Bulk Analysis")

# --- 5. EXECUTION LOGIC ---
if run_analysis and uploaded_file and sitemap_url:
    try:
        # Fetch and Parse Sitemap
        with st.status("Gathering URLs from Sitemap...", expanded=True) as status:
            sitemap_res = requests.get(sitemap_url)
            sitemap_soup = BeautifulSoup(sitemap_res.content, 'xml')
            # Extract all <loc> tags
            all_urls = [loc.text for loc in sitemap_soup.find_all('loc')]
            all_urls = list(set(all_urls))[:max_pages] # Remove duplicates and limit
            
            st.write(f"Found {len(all_urls)} pages to scan.")
            
            results = []
            progress_bar = st.progress(0)
            
            # Start Loop
            for idx, row in df_targets.iterrows():
                target_url = str(row.iloc[0]).strip()
                keyword = str(row.iloc[1]).strip().lower()
                norm_target = normalize_url(target_url)
                
                status.write(f"Searching for: **{keyword}** (Targeting {target_url})")
                
                for site_url in all_urls:
                    # Skip if the site_url is the target itself
                    if normalize_url(site_url) == norm_target:
                        continue
                    
                    html = fetch_content(site_url)
                    if not html:
                        continue
                        
                    soup = BeautifulSoup(html, 'html.parser')
                    text = soup.get_text().lower()
                    
                    if debug_mode:
                        st.write(f"Checking {site_url}... (Text length: {len(text)})")

                    # Logic: Is keyword present?
                    if keyword in text:
                        # Logic: Is target URL already linked?
                        links = [normalize_url(a.get('href')) for a in soup.find_all('a', href=True)]
                        
                        if norm_target not in links:
                            results.append({
                                "Target Keyword": keyword,
                                "Found on Page": site_url,
                                "Missing Link To": target_url
                            })
                
                # Update UI Progress
                progress_bar.progress((idx + 1) / len(df_targets))
            
            status.update(label="✅ Analysis Complete!", state="complete", expanded=False)

        # --- 6. DISPLAY RESULTS ---
        if results:
            df_results = pd.DataFrame(results)
            st.subheader("🎯 Link Opportunities Found")
            
            # Metrics
            m1, m2 = st.columns(2)
            m1.metric("Total Gaps", len(df_results))
            m2.metric("Unique Pages", df_results['Found on Page'].nunique())
            
            st.dataframe(df_results, use_container_width=True)
            
            # Download Button
            csv_data = df_results.to_csv(index=False).encode('utf-8')
            st.download_button("📩 Download CSV Report", csv_data, "link_opportunities.csv", "text/csv")
        else:
            st.warning("No unlinked mentions found. Double-check your Sitemap URL or increase the Scan Limit.")
            if debug_mode:
                st.info("DEBUG: Try checking a URL manually that you KNOW has the keyword to see if the script can read the text.")

    except Exception as e:
        st.error(f"Error: {e}")

else:
    if run_analysis:
        st.error("Please provide both a CSV and a Sitemap URL.")

# Footer
st.markdown("---")
st.caption("SEO Link Pro | Built with Streamlit & Python")
