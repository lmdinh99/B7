# AI Lead Scoring & Automation System (Real Estate)

Dự án tự động hóa thu thập dữ liệu khách hàng từ Google Sheets, chấm điểm tiềm năng offline theo bộ quy tắc nghiệp vụ bất động sản, kiểm duyệt trực quan và xuất báo cáo Excel bàn giao.

## 🚀 Các tính năng chính
1. **Chấm điểm Offline tự động (`app_lead_scoring.py`)**: Chạy độc lập qua dòng lệnh (CLI), phân tích và phân loại 500 khách hàng ngay lập tức mà không cần bất kỳ API Key nào.
2. **Giao diện Web App Streamlit (`streamlit_app.py`)**: Cho phép kiểm duyệt thực tế (Human-in-the-loop), thay đổi điểm số, phân loại và trạng thái duyệt trực tiếp trên giao diện bảng tương tác.
3. **Báo cáo Excel chuyên nghiệp**: Tải xuống file Excel đã định dạng cột tự động để bàn giao.

## 🛠 Hướng dẫn cài đặt và chạy ứng dụng

### 1. Cài đặt các thư viện cần thiết
Mở Terminal/Command Prompt tại thư mục dự án và chạy lệnh:
```bash
pip install -r requirements.txt
python app_lead_scoring.py
streamlit run streamlit_app.py
