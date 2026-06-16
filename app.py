import os
import json
import urllib.request
import pandas as pd
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai

app = FastAPI()

CACHE_FILE = "scored_leads.json"

class LeadItem(BaseModel):
    id: str
    ten_khach: str
    sdt: str
    nhu_cau_mo_ta: str
    score: Optional[int] = None
    classification: Optional[str] = None
    matched_positive_criteria: Optional[List[str]] = []
    matched_negative_criteria: Optional[List[str]] = []
    explanation: Optional[str] = None
    budget: Optional[str] = None
    property_type: Optional[str] = None
    location: Optional[str] = None
    urgency: Optional[str] = None
    status: Optional[str] = "Chờ duyệt" # "Chờ duyệt", "Đồng ý", "Từ chối"

def load_cached_leads():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cached_leads(leads_dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(leads_dict, f, ensure_ascii=False, indent=2)

@app.get("/api/leads")
def get_leads(sheet_url: Optional[str] = None):
    # Default URL if none provided
    if not sheet_url:
        sheet_url = "https://docs.google.com/spreadsheets/d/16tCAf_qqtgYZxoumYQKMEOdBhKE0wg5A/export?format=csv&gid=1542775777"
    else:
        # Convert edit link to export CSV link if needed
        if "edit" in sheet_url:
            if "gid=" in sheet_url:
                gid = sheet_url.split("gid=")[1].split("#")[0]
                base = sheet_url.split("/edit")[0]
                sheet_url = f"{base}/export?format=csv&gid={gid}"
            else:
                base = sheet_url.split("/edit")[0]
                sheet_url = f"{base}/export?format=csv"
    
    try:
        # Download the CSV
        local_filename, _ = urllib.request.urlretrieve(sheet_url)
        df = pd.read_csv(local_filename)
        df = df.fillna("")
        
        cached = load_cached_leads()
        
        leads = []
        for _, row in df.iterrows():
            lead_id = str(row.get("id", ""))
            if not lead_id:
                continue
            
            cached_item = cached.get(lead_id, {})
            
            lead = LeadItem(
                id=lead_id,
                ten_khach=str(row.get("ten_khach", "")),
                sdt=str(row.get("sdt", "")),
                nhu_cau_mo_ta=str(row.get("nhu_cau_mo_ta", "")),
                score=cached_item.get("score"),
                classification=cached_item.get("classification"),
                matched_positive_criteria=cached_item.get("matched_positive_criteria", []),
                matched_negative_criteria=cached_item.get("matched_negative_criteria", []),
                explanation=cached_item.get("explanation"),
                budget=cached_item.get("budget"),
                property_type=cached_item.get("property_type"),
                location=cached_item.get("location"),
                urgency=cached_item.get("urgency"),
                status=cached_item.get("status", "Chờ duyệt")
            )
            leads.append(lead)
            
        return leads
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể tải hoặc xử lý file Google Sheets: {str(e)}")

class ScoreRequest(BaseModel):
    lead_id: str
    nhu_cau_mo_ta: str

@app.post("/api/score")
def score_lead(req: ScoreRequest, x_gemini_key: Optional[str] = Header(None)):
    if not x_gemini_key:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp Gemini API Key trong phần Cài đặt.")
    
    # Read lead_scoring_skill.md for prompt guidance
    skill_content = ""
    if os.path.exists("lead_scoring_skill.md"):
        with open("lead_scoring_skill.md", "r", encoding="utf-8") as f:
            skill_content = f.read()
    else:
        raise HTTPException(status_code=500, detail="Không tìm thấy file định nghĩa quy tắc lead_scoring_skill.md")
        
    try:
        genai.configure(api_key=x_gemini_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        
        prompt = f"""
{skill_content}

Hãy phân tích và chấm điểm yêu cầu khách hàng sau đây:
"{req.nhu_cau_mo_ta}"

Trả về kết quả dưới dạng JSON chính xác theo cấu trúc được mô tả.
"""
        
        response = model.generate_content(prompt)
        res_json = json.loads(response.text.strip())
        
        # Save to cache
        cached = load_cached_leads()
        lead_id = req.lead_id
        
        # Ensure we preserve human status if already set
        current_status = cached.get(lead_id, {}).get("status", "Chờ duyệt")
        
        cached[lead_id] = {
            "score": res_json.get("score"),
            "classification": res_json.get("classification"),
            "matched_positive_criteria": res_json.get("matched_positive_criteria", []),
            "matched_negative_criteria": res_json.get("matched_negative_criteria", []),
            "explanation": res_json.get("explanation"),
            "budget": res_json.get("extracted_info", {}).get("budget"),
            "property_type": res_json.get("extracted_info", {}).get("property_type"),
            "location": res_json.get("extracted_info", {}).get("location"),
            "urgency": res_json.get("extracted_info", {}).get("urgency"),
            "status": current_status
        }
        
        save_cached_leads(cached)
        return cached[lead_id]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi chấm điểm bằng AI: {str(e)}")

class UpdateStatusRequest(BaseModel):
    lead_id: str
    status: str
    score: int
    classification: str

@app.post("/api/update_lead")
def update_lead(req: UpdateStatusRequest):
    cached = load_cached_leads()
    if req.lead_id in cached:
        cached[req.lead_id]["status"] = req.status
        cached[req.lead_id]["score"] = req.score
        cached[req.lead_id]["classification"] = req.classification
    else:
        cached[req.lead_id] = {
            "status": req.status,
            "score": req.score,
            "classification": req.classification
        }
    save_cached_leads(cached)
    return {"status": "success"}

@app.post("/api/export")
def export_leads(leads: List[LeadItem]):
    try:
        data = []
        for lead in leads:
            data.append({
                "ID": lead.id,
                "Tên Khách Hàng": lead.ten_khach,
                "Số Điện Thoại": lead.sdt,
                "Mô Tả Nhu Cầu": lead.nhu_cau_mo_ta,
                "Điểm Số": lead.score if lead.score is not None else "",
                "Phân Loại": lead.classification or "",
                "Tiêu Chí Cộng": ", ".join(lead.matched_positive_criteria or []),
                "Tiêu Chí Trừ": ", ".join(lead.matched_negative_criteria or []),
                "Ngân Sách": lead.budget or "",
                "Loại Hình": list_to_str(lead.property_type),
                "Khu Vực": list_to_str(lead.location),
                "Cấp Thiết": lead.urgency or "",
                "Giải Thích": lead.explanation or "",
                "Trạng Thái Duyệt": lead.status
            })
            
        df = pd.DataFrame(data)
        
        # Save to temp file
        temp_file = "leads_export.xlsx"
        
        # Apply premium formatting using openpyxl engine
        with pd.ExcelWriter(temp_file, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Leads Scored")
            workbook = writer.book
            worksheet = writer.sheets["Leads Scored"]
            
            # Format columns
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 50)
                
        # Read file bytes to return
        with open(temp_file, "rb") as f:
            file_bytes = f.read()
            
        os.remove(temp_file)
        
        return Response(
            content=file_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=leads_report.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể xuất file Excel: {str(e)}")

def list_to_str(val):
    if isinstance(val, list):
        return ", ".join(val)
    return str(val) if val else ""

# Serve frontend files
@app.get("/")
def read_index():
    return FileResponse("index.html")

app.mount("/", StaticFiles(directory="."), name="static")
