import re
import pandas as pd
import requests
import os

# Configuration
SHEET_URL = "https://docs.google.com/spreadsheets/d/16tCAf_qqtgYZxoumYQKMEOdBhKE0wg5A/export?format=csv&gid=1542775777"
OUTPUT_FILE = "leads_scored_report.xlsx"

# Helper to check budget >= 20 billion
def detect_large_budget(text):
    text_lower = text.lower()
    # Match patterns like "20 tỷ", "30 tỷ", "100 tỷ", etc.
    billion_matches = re.findall(r'(\d+)\s*tỷ', text_lower)
    for match in billion_matches:
        try:
            val = int(match)
            if val >= 20:
                return True
        except ValueError:
            pass
            
    # Phrases matching strong finance
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
    # Ngân sách lớn
    if detect_large_budget(text):
        matched_positives.append("Ngân sách lớn / Tài chính mạnh")
        
    # Loại hình cao cấp
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
            
    # Vị trí đắc địa
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
            
    # Đối tượng khách hàng VIP
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
            
    # Tính cấp thiết & Minh bạch
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
    # Yêu cầu phi thực tế
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
            
    # Không có nhu cầu
    no_need_keywords = ["nhầm số", "không có nhu cầu", "dữ liệu cũ", "nhầm ngành"]
    for kw in no_need_keywords:
        if kw in text_lower:
            matched_negatives.append(f"Không có nhu cầu ({kw})")
            break
            
    # Khách hàng không thiện chí
    uncooperative_keywords = ["hỏi giá cho vui", "chưa có ý định mua", "thái độ không hợp tác"]
    for kw in uncooperative_keywords:
        if kw in text_lower:
            matched_negatives.append(f"Không thiện chí ({kw})")
            break
            
    # Spam/Quảng cáo
    spam_keywords = ["bảo hiểm", "vay vốn", "mời chào dịch vụ", "spam"]
    for kw in spam_keywords:
        if kw in text_lower:
            matched_negatives.append(f"Spam/Quảng cáo ({kw})")
            break
            
    # Thông tin liên lạc lỗi
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
    
    # Classification
    if score >= 90:
        classification = "VIP"
    elif score >= 60:
        classification = "Tiềm năng"
    elif score == 50:
        classification = "Trung bình"
    else:
        classification = "Không tiềm năng"
        
    # Auto explanation generator
    reasons = []
    if matched_positives:
        reasons.append("Khách hàng thỏa mãn các tiêu chí tiềm năng: " + ", ".join(matched_positives))
    if matched_negatives:
        reasons.append("Phát hiện yếu tố không tiềm năng: " + ", ".join(matched_negatives))
        
    if not reasons:
        explanation = "Khách hàng có nhu cầu trung bình, chưa khớp các tiêu chí VIP hoặc các dấu hiệu rác."
    else:
        explanation = ". ".join(reasons)
        
    return score, classification, ", ".join(matched_positives), ", ".join(matched_negatives), explanation

def main():
    print("=== STARTING REAL ESTATE LEAD SCORING SYSTEM (OFFLINE) ===")
    print(f"Downloading data from: {SHEET_URL}")
    
    try:
        # Download and read CSV
        response = requests.get(SHEET_URL)
        response.raise_for_status()
        
        # Save temp file
        temp_csv = "temp_leads.csv"
        with open(temp_csv, "wb") as f:
            f.write(response.content)
            
        df = pd.read_csv(temp_csv)
        df = df.fillna("")
        os.remove(temp_csv)
        
        print(f"Downloaded successfully: {len(df)} rows.")
        
        # Score leads
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
        
        # Save output using pandas excel writer
        print(f"Exporting to excel: {OUTPUT_FILE}")
        with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Danh sách Lead")
            
            # Auto-fit columns
            worksheet = writer.sheets["Danh sách Lead"]
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 50)
                
        print("\n=== STATISTICS OVERVIEW ===")
        # Map values to ASCII to avoid terminal print errors
        stats = df["Phân Loại"].value_counts()
        ascii_stats = {}
        for idx, val in stats.items():
            if idx == "Không tiềm năng":
                ascii_stats["Khong tiem nang"] = val
            elif idx == "Tiềm năng":
                ascii_stats["Tiem nang"] = val
            elif idx == "Trung bình":
                ascii_stats["Trung binh"] = val
            else:
                ascii_stats[idx] = val
        for k, v in ascii_stats.items():
            print(f"{k}: {v}")
        print(f"\n=> Report generated successfully at: {os.path.abspath(OUTPUT_FILE)}")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    main()
