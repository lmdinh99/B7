import streamlit as st
import pandas as pd
import requests
import io
from app_lead_scoring import score_lead, SHEET_URL

# Page configuration
st.set_page_config(
    page_title="AI Lead Scoring Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling to look exactly like the premium dark theme
st.markdown("""
<style>
    /* Dark theme overrides */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #58a6ff;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        color: #8b949e;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    /* Metric styling */
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem;
        font-weight: 700;
        color: #58a6ff;
        text-align: center;
    }
    div[data-testid="stMetricLabel"] {
        text-align: center;
        color: #8b949e;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for data
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

# --- SIDEBAR ---
st.sidebar.markdown("### ⚙️ Cấu hình hệ thống")
sheet_url_input = st.sidebar.text_input(
    "Đường dẫn Google Sheets (CSV Export)", 
    value="https://docs.google.com/spreadsheets/d/16tCAf_qqtgYZxoumYQKMEOdBhKE0wg5A/export?format=csv&gid=1542775777"
)

st.sidebar.markdown("### 🔍 Bộ lọc hiển thị")
search_query = st.sidebar.text_input("Tìm kiếm theo Tên / Số điện thoại", "")

# AI Classifications matching the screenshot categories
class_options = ["VIP", "Tiềm năng trung bình", "Không tiềm năng"]
filter_classes = st.sidebar.multiselect(
    "Phân loại của AI", 
    options=class_options,
    default=class_options
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 💡 Quy tắc chấm điểm chính:
* **Cộng 50đ (Khách VIP - Đạt 100đ)**: Ngân sách $\ge$ 20 tỷ; Tìm biệt thự đơn lập, penthouse, shophouse mặt đường lớn, quỹ đất lớn; Vị trí đắc địa (Q1, ven sông, Phú Mỹ Hưng...); Yêu cầu pháp lý 100%, gặp trực tiếp CĐT.
* **Trừ 50đ (Khách Rác - Về 0đ)**: Yêu cầu phi thực tế (giá rẻ vô lý); Không có nhu cầu/nhầm số; Spam/Quảng cáo; Thuê bao/không liên lạc được.
""")

# --- MAIN PAGE ---
st.markdown('<div class="main-title">AI LEAD SCORING DASHBOARD</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Bảng điều khiển phân tích & chấm điểm khách hàng tiềm năng tự động</div>', unsafe_allow_html=True)

# Trigger button for loading data
if st.button("📊 Tải dữ liệu & Chấm điểm từ Google Sheet", type="primary"):
    with st.spinner("Đang xử lý dữ liệu..."):
        try:
            response = requests.get(sheet_url_input)
            response.raise_for_status()
            
            csv_data = io.StringIO(response.text)
            df = pd.read_csv(csv_data)
            df = df.fillna("")
            
            scores = []
            classifications = []
            positives = []
            negatives = []
            explanations = []
            statuses = []
            
            for idx, row in df.iterrows():
                score, classification, pos, neg, exp = score_lead(row)
                # Map classifications to match screenshot categories
                if classification == "Trung bình" or classification == "Tiềm năng":
                    classification = "Tiềm năng trung bình"
                
                scores.append(score)
                classifications.append(classification)
                positives.append(pos)
                negatives.append(neg)
                explanations.append(exp)
                statuses.append("Chờ duyệt")
                
            df_scored = df.copy()
            df_scored["Điểm Số"] = scores
            df_scored["Phân Loại"] = classifications
            df_scored["Tiêu Chí Cộng"] = positives
            df_scored["Tiêu Chí Trừ"] = negatives
            df_scored["Giải Thích Chi Tiết"] = explanations
            df_scored["Trạng Thái Duyệt"] = statuses
            
            st.session_state.processed_data = df_scored
            st.success(f"Đã xử lý thành công {len(df_scored)} dòng dữ liệu!")
        except Exception as e:
            st.error(f"Lỗi khi tải hoặc chấm điểm: {str(e)}")

# Display data if processed
if st.session_state.processed_data is not None:
    df_active = st.session_state.processed_data.copy()
    
    # Apply sidebar filter for search
    if search_query:
        search_query_lower = search_query.lower()
        df_active = df_active[
            df_active["ten_khach"].str.lower().str.contains(search_query_lower) |
            df_active["sdt"].astype(str).str.contains(search_query_lower)
        ]
        
    # Apply sidebar filter for classifications
    if filter_classes:
        df_active = df_active[df_active["Phân Loại"].isin(filter_classes)]
        
    # 1. Metric Cards
    total_leads = len(df_active)
    vip_leads = len(df_active[df_active["Phân Loại"] == "VIP"])
    potential_leads = len(df_active[df_active["Phân Loại"] == "Tiềm năng trung bình"])
    junk_leads = len(df_active[df_active["Phân Loại"] == "Không tiềm năng"])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("TỔNG KHÁCH HÀNG", total_leads)
    with col2:
        st.metric("KHÁCH HÀNG VIP", vip_leads)
    with col3:
        st.metric("TIỀM NĂNG TRUNG BÌNH", potential_leads)
    with col4:
        st.metric("KHÔNG TIỀM NĂNG", junk_leads)
        
    st.markdown("### 📊 Biểu đồ phân tích trực quan")
    
    # 2. Charts side-by-side
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("#### 📈 Tỉ lệ phân loại Khách hàng")
        class_counts = df_active["Phân Loại"].value_counts().reset_index()
        class_counts.columns = ["Phân loại", "Số lượng"]
        st.bar_chart(class_counts.set_index("Phân loại"))
        
    with col_chart2:
        st.markdown("#### 📈 Phân bố điểm số tiềm năng")
        score_counts = df_active["Điểm Số"].value_counts().reset_index()
        score_counts.columns = ["Điểm Số", "Số lượng"]
        st.bar_chart(score_counts.set_index("Điểm Số"))
        
    st.markdown("---")
    
    # 3. Interactive Data Editor (Human-in-the-loop)
    st.markdown("### 📋 Danh sách chi tiết khách hàng và Phê duyệt")
    
    edited_df = st.data_editor(
        df_active,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "ten_khach": st.column_config.TextColumn("Tên Khách Hàng", disabled=True),
            "sdt": st.column_config.TextColumn("Số Điện Thoại", disabled=True),
            "nhu_cau_mo_ta": st.column_config.TextColumn("Mô tả nhu cầu", disabled=True, width="large"),
            "Điểm Số": st.column_config.NumberColumn("Điểm Số", min_value=0, max_value=100),
            "Phân Loại": st.column_config.SelectboxColumn("Phân Loại", options=["VIP", "Tiềm năng trung bình", "Không tiềm năng"]),
            "Trạng Thái Duyệt": st.column_config.SelectboxColumn("Trạng Thái Duyệt", options=["Chờ duyệt", "Đồng ý", "Từ chối"]),
            "Tiêu Chí Cộng": st.column_config.TextColumn("Tiêu Chí Cộng", disabled=True),
            "Tiêu Chí Trừ": st.column_config.TextColumn("Tiêu Chí Trừ", disabled=True),
            "Giải Thích Chi Tiết": st.column_config.TextColumn("Giải thích", disabled=True),
        },
        disabled=["id", "ten_khach", "sdt", "nhu_cau_mo_ta", "Tiêu Chí Cộng", "Tiêu Chí Trừ", "Giải Thích Chi Tiết"],
        hide_index=True,
        use_container_width=True,
        key="data_editor"
    )
    
    # Sync edits back to session state
    if not edited_df.equals(df_active):
        for idx, row in edited_df.iterrows():
            lead_id = row["id"]
            st.session_state.processed_data.loc[st.session_state.processed_data["id"] == lead_id, ["Điểm Số", "Phân Loại", "Trạng Thái Duyệt"]] = [
                row["Điểm Số"], row["Phân Loại"], row["Trạng Thái Duyệt"]
            ]
            
    # 4. Export button
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        st.session_state.processed_data.to_excel(writer, index=False, sheet_name="Leads Report")
        worksheet = writer.sheets["Leads Report"]
        for col in worksheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 50)
            
    buffer.seek(0)
    
    st.download_button(
        label="📥 Tải xuống báo cáo Excel hoàn chỉnh",
        data=buffer,
        file_name="leads_scored_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
