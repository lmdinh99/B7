import streamlit as st
import pandas as pd
import requests
import io
from app_lead_scoring import score_lead, SHEET_URL

# Page configuration
st.set_page_config(
    page_title="Real Estate Lead Scoring & Automation",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for modern dark/glassmorphic look in Streamlit
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">AI Lead Scoring & Automation</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Hệ thống tự động hóa lấy dữ liệu từ Google Sheets, tự động chấm điểm và hỗ trợ kiểm duyệt kiểm soát chất lượng (Human-in-the-loop)</div>', unsafe_allow_html=True)

# Session state initialization
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = None
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

# Sidebar
st.sidebar.header("Cài đặt Nguồn Dữ Liệu")
sheet_url_input = st.sidebar.text_input("Google Sheet CSV URL", value=SHEET_URL)

if st.sidebar.button("Tải & Đồng bộ Dữ liệu", type="primary"):
    with st.spinner("Đang tải dữ liệu từ Google Sheets..."):
        try:
            response = requests.get(sheet_url_input)
            response.raise_for_status()
            
            # Read CSV
            csv_data = io.StringIO(response.text)
            df = pd.read_csv(csv_data)
            df = df.fillna("")
            
            st.session_state.raw_data = df
            st.sidebar.success(f"Tải thành công {len(df)} dòng dữ liệu!")
            
            # Apply Scoring Engine
            scores = []
            classifications = []
            positives = []
            negatives = []
            explanations = []
            statuses = []
            
            for idx, row in df.iterrows():
                score, classification, pos, neg, exp = score_lead(row)
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
            
        except Exception as e:
            st.sidebar.error(f"Lỗi: {str(e)}")

# Main Content
if st.session_state.processed_data is not None:
    df_active = st.session_state.processed_data
    
    # 1. Statistics Cards
    total_leads = len(df_active)
    vip_leads = len(df_active[df_active["Phân Loại"] == "VIP"])
    potential_leads = len(df_active[df_active["Phân Loại"] == "Tiềm năng"])
    junk_leads = len(df_active[df_active["Phân Loại"] == "Không tiềm năng"])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tổng số Khách Hàng", total_leads)
    with col2:
        st.metric("Khách hàng VIP", vip_leads)
    with col3:
        st.metric("Tiềm Năng", potential_leads)
    with col4:
        st.metric("Không Tiềm Năng (Rác)", junk_leads)
        
    st.markdown("---")
    
    # 2. Filters & Searches
    st.subheader("Bộ lọc & Tìm kiếm")
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        search_query = st.text_input("Tìm kiếm theo Tên, SĐT, Nhu cầu...", "")
    with col_filter2:
        filter_class = st.selectbox("Lọc Phân Loại", ["Tất cả", "VIP", "Tiềm năng", "Trung bình", "Không tiềm năng"])
    with col_filter3:
        filter_status = st.selectbox("Lọc Trạng Thái Duyệt", ["Tất cả", "Chờ duyệt", "Đồng ý", "Từ chối"])
        
    # Apply filters to view
    filtered_df = df_active.copy()
    if search_query:
        search_query = search_query.lower()
        filtered_df = filtered_df[
            filtered_df["ten_khach"].str.lower().str.contains(search_query) | 
            filtered_df["sdt"].astype(str).str.contains(search_query) | 
            filtered_df["nhu_cau_mo_ta"].str.lower().str.contains(search_query)
        ]
    if filter_class != "Tất cả":
        filtered_df = filtered_df[filtered_df["Phân Loại"] == filter_class]
    if filter_status != "Tất cả":
        filtered_df = filtered_df[filtered_df["Trạng Thái Duyệt"] == filter_status]
        
    # 3. Interactive Data Editor (Human-in-the-loop)
    st.subheader("Kiểm duyệt Khách Hàng (Human-in-the-loop)")
    st.info("💡 Bạn có thể trực tiếp sửa cột 'Điểm Số', 'Phân Loại' và 'Trạng Thái Duyệt' ở bảng dưới đây:")
    
    edited_df = st.data_editor(
        filtered_df,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "ten_khach": st.column_config.TextColumn("Tên Khách Hàng", disabled=True),
            "sdt": st.column_config.TextColumn("Số Điện Thoại", disabled=True),
            "nhu_cau_mo_ta": st.column_config.TextColumn("Mô tả nhu cầu", disabled=True, width="large"),
            "Điểm Số": st.column_config.NumberColumn("Điểm Số", min_value=0, max_value=100),
            "Phân Loại": st.column_config.SelectboxColumn("Phân Loại", options=["VIP", "Tiềm năng", "Trung bình", "Không tiềm năng"]),
            "Trạng Thái Duyệt": st.column_config.SelectboxColumn("Trạng Thái Duyệt", options=["Chờ duyệt", "Đồng ý", "Từ chối"]),
            "Tiêu Chí Cộng": st.column_config.TextColumn("Tiêu Chí Cộng", disabled=True),
            "Tiêu Chí Trừ": st.column_config.TextColumn("Tiêu Chí Trừ", disabled=True),
            "Giải Thích Chi Tiết": st.column_config.TextColumn("Giải thích chi tiết", disabled=True, width="medium"),
        },
        disabled=["id", "ten_khach", "sdt", "nhu_cau_mo_ta", "Tiêu Chí Cộng", "Tiêu Chí Trừ", "Giải Thích Chi Tiết"],
        hide_index=True,
        use_container_width=True,
        key="data_editor_table"
    )
    
    # Update back to session state when changes occur
    if not edited_df.equals(filtered_df):
        # Merge edits back to the main dataframe
        for idx, row in edited_df.iterrows():
            lead_id = row["id"]
            st.session_state.processed_data.loc[st.session_state.processed_data["id"] == lead_id, ["Điểm Số", "Phân Loại", "Trạng Thái Duyệt"]] = [
                row["Điểm Số"], row["Phân Loại"], row["Trạng Thái Duyệt"]
            ]
            
    st.markdown("---")
    
    # 4. Export options
    st.subheader("Bàn giao dữ liệu")
    
    # Create excel in memory buffer
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        st.session_state.processed_data.to_excel(writer, index=False, sheet_name="Data Scored")
        # Format columns
        worksheet = writer.sheets["Data Scored"]
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

else:
    st.warning("Vui lòng click nút 'Tải & Đồng bộ Dữ liệu' ở cột bên trái để nạp và chấm điểm danh sách khách hàng.")
