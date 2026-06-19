import os
import re
import io
import sys
import pandas as pd
import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Configuration
conn = st.connection("gsheets", type=GSheetsConnection)
spreadsheet_id = "https://docs.google.com/spreadsheets/d/10W14zS9dL4w1G311MRFri10_XoWCSPCNPJsmITf_--s/edit"
df = conn.read(spreadsheet=spreadsheet_id, worksheet="leads_for_gsheet", ttl="10m")

OUTPUT_FILE = "leads_scored_report.xlsx"

# Helper to check budget >= 20 billion
def detect_large_budget(text):
    text_lower = text.lower()
    billion_matches = re.findall(r'(\d+)\s*tỷ', text_lower)
    for match in billion_matches:
        try:
            val = int(match)
            if val >= 20:
                return True
        except ValueError:
            pass
            
    strong_finance_phrases = ["tài chính mạnh", "không thành vấn đề", "tài chính cực mạnh", "tài chính lớn", "ngân sách lớn"]
    for phrase in strong_finance_phrases:
        if phrase in text_lower:
            return True
            
    return False

# Rule-based Scoring Engine
def score_lead(row):
    text = str(row.get("nhu_cau_mo_ta", ""))
    text_lower = text.lower()
    
    matched_positives = []
    matched_negatives = []
    
    # 1. Evaluate Positive Criteria (+50 pts)
    if detect_large_budget(text):
        matched_positives.append("Ngân sách lớn / Tài chính mạnh")
        
    premium_types = {
        "biệt thự đơn lập": "Biệt thự đơn lập",
        "penthouse": "Penthouse",
        "shophouse mặt đường lớn": "Shophouse mặt đường lớn",
        "quỹ đất công nghiệp": "Quỹ đất công nghiệp",
        "sàn văn phòng diện tích lớn": "Sàn văn phòng diện tích lớn",
        "sàn văn phòng": "Sàn văn phòng"
    }
    for kw, val in premium_types.items():
        if kw in text_lower:
            matched_positives.append(f"Loại hình cao cấp ({val})")
            break
            
    prime_locations = {
        "quận 1": "Quận 1",
        "ven sông": "Ven sông",
        "vinhomes ocean park": "Vinhomes Ocean Park",
        "phú mỹ hưng": "Phú Mỹ Hưng"
    }
    for kw, val in prime_locations.items():
        if kw in text_lower:
            matched_positives.append(f"Vị trí đắc địa ({val})")
            break
            
    vip_profiles = {
        "chủ doanh nghiệp": "Chủ doanh nghiệp",
        "nhà đầu tư chuyên nghiệp": "Nhà đầu tư chuyên nghiệp",
        "mua sỉ": "Mua sỉ",
        "mua số lượng lớn": "Mua số lượng lớn",
        "khách hàng vip": "Khách hàng VIP"
    }
    for kw, val in vip_profiles.items():
        if kw in text_lower:
            matched_positives.append(f"Đối tượng khách hàng VIP ({val})")
            break
            
    urgency_keywords = {
        "pháp lý chuẩn 100%": "Pháp lý chuẩn 100%",
        "sổ hồng riêng": "Sổ hồng riêng",
        "gặp trực tiếp chủ đầu tư để đàm phán": "Muốn gặp trực tiếp chủ đầu tư",
        "gặp trực tiếp chủ đầu tư": "Gặp trực tiếp chủ đầu tư"
    }
    for kw, val in urgency_keywords.items():
        if kw in text_lower:
            matched_positives.append(f"Tính cấp thiết & Minh bạch ({val})")
            break

    # 2. Evaluate Negative Criteria (-50 pts)
    unrealistic_patterns = [
        r"nhà quận 1 giá \d+-\d+ tỷ", 
        r"nhà trung tâm.*giá vài trăm triệu",
        r"nhà thuê nguyên căn giá 2 triệu",
        r"thuê.*giá 2 triệu",
        r"nhà q1 giá 1 tỷ",
        r"đòi mua nhà q1 giá 1 tỷ"
    ]
    for pattern in unrealistic_patterns:
        if re.search(pattern, text_lower) or "nhà quận 1 giá 1-2 tỷ" in text_lower or "giá 2 triệu" in text_lower or "q1 giá 1 tỷ" in text_lower:
            matched_negatives.append("Yêu cầu phi thực tế (Giá thấp vô lý)")
            break
            
    no_need_keywords = ["nhầm số", "không có nhu cầu", "dữ liệu cũ", "nhầm ngành"]
    for kw in no_need_keywords:
        if kw in text_lower:
            matched_negatives.append(f"Không có nhu cầu ({kw})")
            break
            
    uncooperative_keywords = ["hỏi giá cho vui", "chưa có ý định mua", "thái độ không hợp tác"]
    for kw in uncooperative_keywords:
        if kw in text_lower:
            matched_negatives.append(f"Không thiện chí ({kw})")
            break
            
    spam_keywords = ["bảo hiểm", "vay vốn", "mời chào dịch vụ", "spam"]
    for kw in spam_keywords:
        if kw in text_lower:
            matched_negatives.append(f"Spam/Quảng cáo ({kw})")
            break
            
    contact_error_keywords = ["thuê bao", "gọi nhiều lần không bắt máy", "không phản hồi zalo"]
    for kw in contact_error_keywords:
        if kw in text_lower:
            matched_negatives.append(f"Thông tin liên lạc lỗi ({kw})")
            break

    # 3. Score calculation
    base_score = 50
    has_positive = len(matched_positives) > 0
    has_negative = len(matched_negatives) > 0
    
    score = base_score
    if has_positive:
        score += 50
    if has_negative:
        score -= 50
        
    score = max(0, min(100, score))
    
    # Classification matching "Nóng", "Ấm", "Lạnh", "Rác"
    if score >= 90:
        classification = "Nóng"
    elif score >= 60:
        classification = "Ấm"
    elif score == 50:
        classification = "Lạnh"
    else:
        classification = "Rác"
        
    reasons = []
    if matched_positives:
        reasons.append("Cộng điểm: " + ", ".join(matched_positives))
    if matched_negatives:
        reasons.append("Trừ điểm: " + ", ".join(matched_negatives))
        
    if not reasons:
        explanation = "Nhu cầu trung bình, giữ nguyên điểm."
    else:
        explanation = ". ".join(reasons)
        
    return score, classification, ", ".join(matched_positives), ", ".join(matched_negatives), explanation

# Streamlit App Logic
def run_streamlit():
    st.set_page_config(
        page_title="AI Lead Scoring Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Clean high-contrast slate theme styling
    st.markdown("""
    <style>
        .stApp {
            background-color: #0f172a;
            color: #f1f5f9;
            font-family: 'Inter', sans-serif;
        }
        .main-title {
            font-size: 2.6rem;
            font-weight: 800;
            background: linear-gradient(90deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
            text-shadow: 0 2px 8px rgba(56, 189, 248, 0.15);
        }
        .subtitle {
            color: #94a3b8;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }
        .sub-header {
            font-size: 1.6rem;
            font-weight: 700;
            margin-top: 2rem;
            margin-bottom: 0.5rem;
            color: #38bdf8;
            border-left: 5px solid #38bdf8;
            padding-left: 12px;
        }
        .desc-text {
            color: #cbd5e1;
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
        }
        /* Custom Button Styling */
        div.stButton > button {
            background-color: #1e293b !important;
            color: #f1f5f9 !important;
            border: 1px solid #475569 !important;
            border-radius: 8px !important;
            padding: 0.6rem 1.2rem !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }
        div.stButton > button:hover {
            background-color: #334155 !important;
            border-color: #64748b !important;
            color: #ffffff !important;
        }
        /* Primary/Action Button */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(90deg, #0284c7, #4f46e5) !important;
            color: #ffffff !important;
            border: none !important;
            box-shadow: 0 4px 10px rgba(2, 132, 199, 0.3) !important;
        }
        div.stButton > button[kind="primary"]:hover {
            background: linear-gradient(90deg, #0369a1, #4338ca) !important;
            box-shadow: 0 6px 15px rgba(2, 132, 199, 0.5) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None

    # Sidebar settings
    st.sidebar.markdown("### ⚙️ Cấu hình hệ thống")
    sheet_url_input = st.sidebar.text_input("Đường dẫn Google Sheets (CSV Export)", value=SHEET_URL)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 💡 Quy tắc chấm điểm chính:
    * **Cộng 50đ (Khách VIP - Đạt 100đ)**: Ngân sách $\ge$ 20 tỷ; Tìm biệt thự đơn lập, penthouse, shophouse mặt đường lớn, quỹ đất lớn; Vị trí đắc địa (Q1, ven sông, Phú Mỹ Hưng...); Yêu cầu pháp lý 100%, gặp trực tiếp CĐT.
    * **Trừ 50đ (Khách Rác - Về 0đ)**: Yêu cầu phi thực tế (giá rẻ vô lý); Không có nhu cầu/nhầm số; Spam/Quảng cáo; Thuê bao/không liên lạc được.
    """)

    st.markdown('<div class="main-title">AI LEAD SCORING DASHBOARD</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Bảng điều khiển phân tích & chấm điểm khách hàng tiềm năng tự động</div>', unsafe_allow_html=True)

    # Load button
    if st.button("📊 Tải dữ liệu & Chấm điểm từ Google Sheet", type="primary"):
        with st.spinner("Đang xử lý dữ liệu..."):
            try:
                response = requests.get(sheet_url_input)
                response.raise_for_status()
                csv_text = response.content.decode('utf-8-sig')
                csv_data = io.StringIO(csv_text)
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

    if st.session_state.processed_data is not None:
        # Show Metrics
        total_leads = len(st.session_state.processed_data)
        nong_count = len(st.session_state.processed_data[st.session_state.processed_data["Phân Loại"] == "Nóng"])
        am_count = len(st.session_state.processed_data[st.session_state.processed_data["Phân Loại"] == "Ấm"])
        rac_count = len(st.session_state.processed_data[st.session_state.processed_data["Phân Loại"] == "Rác"])
        
        # Show high-contrast premium HTML cards for metric display
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.8); border: 2px solid #38bdf8; border-radius: 12px; padding: 1.25rem; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
                <div style="color: #38bdf8; font-size: 0.95rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Tổng Khách Hàng</div>
                <div style="color: #ffffff; font-size: 2.8rem; font-weight: 800; margin-top: 0.5rem; line-height: 1;">{total_leads}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.8); border: 2px solid #10b981; border-radius: 12px; padding: 1.25rem; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
                <div style="color: #10b981; font-size: 0.95rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Khách Hàng Nóng</div>
                <div style="color: #ffffff; font-size: 2.8rem; font-weight: 800; margin-top: 0.5rem; line-height: 1;">{nong_count}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.8); border: 2px solid #f59e0b; border-radius: 12px; padding: 1.25rem; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
                <div style="color: #f59e0b; font-size: 0.95rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Khách Hàng Ấm</div>
                <div style="color: #ffffff; font-size: 2.8rem; font-weight: 800; margin-top: 0.5rem; line-height: 1;">{am_count}</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.8); border: 2px solid #ef4444; border-radius: 12px; padding: 1.25rem; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
                <div style="color: #ef4444; font-size: 0.95rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Khách Hàng Rác</div>
                <div style="color: #ffffff; font-size: 2.8rem; font-weight: 800; margin-top: 0.5rem; line-height: 1;">{rac_count}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 2. Bảng Kiểm Duyệt Section
        st.markdown('<div class="sub-header">📝 2. Bảng Kiểm Duyệt (Dành cho Kế Toán / Sales)</div>', unsafe_allow_html=True)
        st.markdown('<div class="desc-text">Hệ thống đã tự động gán Từ khóa (Tags) và Gợi ý hành động. Bạn có thể dùng bộ lọc dưới đây để tìm và phê duyệt khách hàng nhanh chóng.</div>', unsafe_allow_html=True)
        
        st.markdown("#### 🔎 Bộ Lọc Dữ Liệu Thông Minh")
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            filter_classes = st.multiselect(
                "Lọc theo Phân loại AI:",
                options=["Nóng", "Ấm", "Lạnh", "Rác"],
                default=["Nóng", "Ấm", "Lạnh", "Rác"]
            )
        with col_filter2:
            filter_statuses = st.multiselect(
                "Lọc theo Trạng thái duyệt:",
                options=["Chờ duyệt", "Đồng ý", "Từ chối"],
                default=["Chờ duyệt", "Đồng ý", "Từ chối"]
            )
            
        st.markdown("---")
        
        # Action buttons
        st.markdown("#### ⚡ Hành Động Nhanh")
        col_btn1, col_btn2, col_btn_empty = st.columns([1.5, 1.5, 3])
        
        with col_btn1:
            if st.button("✅ Phê duyệt toàn bộ khách Nóng & Ấm", type="primary", use_container_width=True):
                # Update status of Nong & Am to Dong y
                mask = st.session_state.processed_data["Phân Loại"].isin(["Nóng", "Ấm"])
                st.session_state.processed_data.loc[mask, "Trạng Thái Duyệt"] = "Đồng ý"
                st.toast("Đã phê duyệt toàn bộ khách hàng Nóng & Ấm!")
                st.rerun()
                
        with col_btn2:
            if st.button("🗑️ Loại bỏ toàn bộ khách Rác", use_container_width=True):
                # Update status of Rac to Tu choi
                mask = st.session_state.processed_data["Phân Loại"] == "Rác"
                st.session_state.processed_data.loc[mask, "Trạng Thái Duyệt"] = "Từ chối"
                st.toast("Đã từ chối toàn bộ khách hàng Rác!")
                st.rerun()
                
        # Apply filters to view
        df_active = st.session_state.processed_data.copy()
        if filter_classes:
            df_active = df_active[df_active["Phân Loại"].isin(filter_classes)]
        if filter_statuses:
            df_active = df_active[df_active["Trạng Thái Duyệt"].isin(filter_statuses)]
            
        # Display data editor
        edited_df = st.data_editor(
            df_active,
            column_config={
                "id": st.column_config.NumberColumn("Mã KH", disabled=True),
                "ten_khach": st.column_config.TextColumn("Tên Khách Hàng", disabled=True),
                "sdt": st.column_config.TextColumn("Số Điện Thoại", disabled=True),
                "nhu_cau_mo_ta": st.column_config.TextColumn("Ghi chú Nhu cầu", disabled=True, width="large"),
                "Điểm Số": st.column_config.NumberColumn("Điểm AI", min_value=0, max_value=100),
                "Phân Loại": st.column_config.SelectboxColumn("Phân loại", options=["Nóng", "Ấm", "Lạnh", "Rác"]),
                "Trạng Thái Duyệt": st.column_config.SelectboxColumn("Trạng Thái Duyệt", options=["Chờ duyệt", "Đồng ý", "Từ chối"]),
                "Tiêu Chí Cộng": st.column_config.TextColumn("Từ khóa (Tags)", disabled=True),
                "Tiêu Chí Trừ": st.column_config.TextColumn("Tiêu Chí Trừ", disabled=True),
                "Giải Thích Chi Tiết": st.column_config.TextColumn("Giải thích", disabled=True),
            },
            disabled=["id", "ten_khach", "sdt", "nhu_cau_mo_ta", "Tiêu Chí Cộng", "Tiêu Chí Trừ", "Giải Thích Chi Tiết"],
            hide_index=True,
            use_container_width=True,
            key="data_editor"
        )
        
        # Save edits back
        if not edited_df.equals(df_active):
            for idx, row in edited_df.iterrows():
                lead_id = row["id"]
                st.session_state.processed_data.loc[st.session_state.processed_data["id"] == lead_id, ["Điểm Số", "Phân Loại", "Trạng Thái Duyệt"]] = [
                    row["Điểm Số"], row["Phân Loại"], row["Trạng Thái Duyệt"]
                ]
                
        # Export Excel Button
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            st.session_state.processed_data.to_excel(writer, index=False, sheet_name="Leads Report")
            worksheet = writer.sheets["Leads Report"]
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 50)
        buffer.seek(0)
        
        st.markdown(" ")
        st.download_button(
            label="📥 Tải xuống báo cáo Excel hoàn chỉnh",
            data=buffer,
            file_name="leads_scored_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

# Command line interface execution
def run_cli():
    print("=== STARTING REAL ESTATE LEAD SCORING SYSTEM (OFFLINE CLI) ===")
    print(f"Downloading data from: {SHEET_URL}")
    
    try:
        response = requests.get(SHEET_URL)
        response.raise_for_status()
        
        csv_text = response.content.decode('utf-8-sig')
        temp_csv = "temp_leads.csv"
        with open(temp_csv, "w", encoding="utf-8") as f:
            f.write(csv_text)
            
        df = pd.read_csv(temp_csv, encoding="utf-8")
        df = df.fillna("")
        os.remove(temp_csv)
        
        print(f"Downloaded successfully: {len(df)} rows.")
        
        scores = []
        classifications = []
        positives = []
        negatives = []
        explanations = []
        
        for idx, row in df.iterrows():
            score, classification, pos, neg, exp = score_lead(row)
            scores.append(score)
            classifications.append(classification)
            positives.append(pos)
            negatives.append(neg)
            explanations.append(exp)
            
        df["Điểm Số"] = scores
        df["Phân Loại"] = classifications
        df["Tiêu Chí Cộng"] = positives
        df["Tiêu Chí Trừ"] = negatives
        df["Giải Thích Chi Tiết"] = explanations
        
        print(f"Exporting to excel: {OUTPUT_FILE}")
        with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Danh sách Lead")
            worksheet = writer.sheets["Danh sách Lead"]
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 50)
                
        print("\n=== STATISTICS OVERVIEW ===")
        stats = df["Phân Loại"].value_counts()
        ascii_stats = {}
        for idx, val in stats.items():
            if idx == "Rác":
                ascii_stats["Rac"] = val
            elif idx == "Nóng":
                ascii_stats["Nong"] = val
            elif idx == "Ấm":
                ascii_stats["Am"] = val
            elif idx == "Lạnh":
                ascii_stats["Lanh"] = val
            else:
                ascii_stats[idx] = val
        for k, v in ascii_stats.items():
            print(f"{k}: {v}")
        print(f"\n=> Report generated successfully at: {os.path.abspath(OUTPUT_FILE)}")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    if st.runtime.exists():
        run_streamlit()
    else:
        run_cli()
