// Global State
let allLeads = [];
let filteredLeads = [];
let currentPage = 1;
const itemsPerPage = 15;
let geminiKey = localStorage.getItem("gemini_key") || "";
let sheetUrl = localStorage.getItem("sheet_url") || "https://docs.google.com/spreadsheets/d/16tCAf_qqtgYZxoumYQKMEOdBhKE0wg5A/edit?gid=1542775777";
let activeLeadId = null;
let isScoringAll = false;
let stopScoringRequested = false;

// DOM Elements
const navDashboard = document.getElementById("nav-dashboard");
const navLeads = document.getElementById("nav-leads");
const navSettings = document.getElementById("nav-settings");

const viewDashboard = document.getElementById("view-dashboard");
const viewLeads = document.getElementById("view-leads");
const viewSettings = document.getElementById("view-settings");

const pageTitle = document.getElementById("page-title");
const pageSubtitle = document.getElementById("page-subtitle");

const btnImportSheet = document.getElementById("btn-import-sheet");
const btnExportExcel = document.getElementById("btn-export-excel");
const btnRunAllScoring = document.getElementById("btn-run-all-scoring");
const btnStopScoring = document.getElementById("btn-stop-scoring");

const statTotal = document.getElementById("stat-total");
const statVip = document.getElementById("stat-vip");
const statPotential = document.getElementById("stat-potential");
const statJunk = document.getElementById("stat-junk");

const scoringProgressBar = document.getElementById("scoring-progress-bar");
const scoringProgressText = document.getElementById("scoring-progress-text");

const searchInput = document.getElementById("search-input");
const filterClassification = document.getElementById("filter-classification");
const filterStatus = document.getElementById("filter-status");

const leadsTbody = document.getElementById("leads-tbody");
const paginationControls = document.getElementById("pagination-controls");

// Settings Elements
const settingsGeminiKey = document.getElementById("settings-gemini-key");
const settingsSheetUrl = document.getElementById("settings-sheet-url");
const btnSaveSettings = document.getElementById("btn-save-settings");
const btnToggleKey = document.getElementById("btn-toggle-key");

// Modal Elements
const reviewModal = document.getElementById("review-modal");
const btnCloseModal = document.getElementById("btn-close-modal");
const btnModalCancel = document.getElementById("btn-modal-cancel");
const btnModalSave = document.getElementById("btn-modal-save");

const modalName = document.getElementById("modal-name");
const modalPhone = document.getElementById("modal-phone");
const modalDesc = document.getElementById("modal-desc");
const modalScore = document.getElementById("modal-score");
const modalClass = document.getElementById("modal-class");
const modalPositives = document.getElementById("modal-positives");
const modalNegatives = document.getElementById("modal-negatives");
const modalBudget = document.getElementById("modal-budget");
const modalType = document.getElementById("modal-type");
const modalLocation = document.getElementById("modal-location");
const modalUrgency = document.getElementById("modal-urgency");
const modalExplanation = document.getElementById("modal-explanation");

const adjustScore = document.getElementById("adjust-score");
const adjustClass = document.getElementById("adjust-class");
const statusBtnGroup = document.querySelector(".status-btn-group");

// Toast Notification
function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "fa-circle-check";
    if (type === "error") icon = "fa-circle-xmark";
    
    toast.innerHTML = `<i class="fa-solid ${icon}"></i><span>${message}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = "slideIn 0.3s reverse";
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Navigation Tabs
function switchView(tabId) {
    [navDashboard, navLeads, navSettings].forEach(btn => btn.classList.remove("active"));
    [viewDashboard, viewLeads, viewSettings].forEach(sec => sec.classList.remove("active"));
    
    if (tabId === "dashboard") {
        navDashboard.classList.add("active");
        viewDashboard.classList.add("active");
        pageTitle.innerText = "Bảng điều khiển";
        pageSubtitle.innerText = "Hệ thống phân tích và chấm điểm khách hàng tiềm năng bằng AI";
        updateStats();
    } else if (tabId === "leads") {
        navLeads.classList.add("active");
        viewLeads.classList.add("active");
        pageTitle.innerText = "Danh sách khách hàng";
        pageSubtitle.innerText = "Xem, tìm kiếm, sửa điểm số và trạng thái duyệt khách hàng";
        renderLeadsTable();
    } else if (tabId === "settings") {
        navSettings.classList.add("active");
        viewSettings.classList.add("active");
        pageTitle.innerText = "Cài đặt hệ thống";
        pageSubtitle.innerText = "Cấu hình Google Sheets và Gemini API Key";
    }
}

navDashboard.addEventListener("click", () => switchView("dashboard"));
navLeads.addEventListener("click", () => switchView("leads"));
navSettings.addEventListener("click", () => switchView("settings"));

// Toggle Gemini Key Visibility
btnToggleKey.addEventListener("click", () => {
    const type = settingsGeminiKey.type === "password" ? "text" : "password";
    settingsGeminiKey.type = type;
    const icon = btnToggleKey.querySelector("i");
    icon.className = type === "password" ? "fa-solid fa-eye" : "fa-solid fa-eye-slash";
});

// Load settings into UI
settingsGeminiKey.value = geminiKey;
settingsSheetUrl.value = sheetUrl;

// Save Settings
btnSaveSettings.addEventListener("click", () => {
    geminiKey = settingsGeminiKey.value.trim();
    sheetUrl = settingsSheetUrl.value.trim();
    localStorage.setItem("gemini_key", geminiKey);
    localStorage.setItem("sheet_url", sheetUrl);
    showToast("Đã lưu các thiết lập cấu hình!");
});

// Fetch Leads Data from Backend
async function fetchLeads() {
    try {
        const res = await fetch(`/api/leads?sheet_url=${encodeURIComponent(sheetUrl)}`);
        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Có lỗi xảy ra khi gọi API.");
        }
        allLeads = await res.json();
        filteredLeads = [...allLeads];
        updateStats();
        showToast(`Đồng bộ dữ liệu thành công! Tìm thấy ${allLeads.length} dòng.`);
    } catch (e) {
        showToast(e.message, "error");
    }
}

btnImportSheet.addEventListener("click", fetchLeads);

// Calculate Stats
function updateStats() {
    const total = allLeads.length;
    const vip = allLeads.filter(l => l.classification === "VIP").length;
    const potential = allLeads.filter(l => l.classification === "Tiềm năng").length;
    const junk = allLeads.filter(l => l.classification === "Không tiềm năng").length;
    const scored = allLeads.filter(l => l.score !== null).length;
    
    statTotal.innerText = total;
    statVip.innerText = vip;
    statPotential.innerText = potential;
    statJunk.innerText = junk;
    
    const percentage = total > 0 ? Math.round((scored / total) * 100) : 0;
    scoringProgressBar.style.width = `${percentage}%`;
    scoringProgressText.innerText = `Đã chấm điểm: ${scored} / ${total} (${percentage}%)`;
}

// Render Leads Table
function renderLeadsTable() {
    leadsTbody.innerHTML = "";
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageItems = filteredLeads.slice(startIndex, endIndex);
    
    if (pageItems.length === 0) {
        leadsTbody.innerHTML = `<tr><td colspan="8" style="text-align:center;">Không tìm thấy khách hàng nào.</td></tr>`;
        paginationControls.innerHTML = "";
        return;
    }
    
    pageItems.forEach(lead => {
        const tr = document.createElement("tr");
        
        let classBadge = `<span class="badge badge-none">Chưa chấm</span>`;
        if (lead.classification === "VIP") classBadge = `<span class="badge badge-vip">VIP</span>`;
        else if (lead.classification === "Tiềm năng") classBadge = `<span class="badge badge-potential">Tiềm năng</span>`;
        else if (lead.classification === "Trung bình") classBadge = `<span class="badge badge-neutral">Trung bình</span>`;
        else if (lead.classification === "Không tiềm năng") classBadge = `<span class="badge badge-junk">K. Tiềm năng</span>`;
        
        let statusBadge = `<span class="badge badge-status-waiting">Chờ duyệt</span>`;
        if (lead.status === "Đồng ý") statusBadge = `<span class="badge badge-status-approved">Đồng ý</span>`;
        else if (lead.status === "Từ chối") statusBadge = `<span class="badge badge-status-rejected">Từ chối</span>`;
        
        const scoreDisplay = lead.score !== null ? lead.score : "-";
        
        tr.innerHTML = `
            <td>${lead.id}</td>
            <td><strong>${lead.ten_khach}</strong></td>
            <td>${lead.sdt}</td>
            <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${lead.nhu_cau_mo_ta}</td>
            <td><strong>${scoreDisplay}</strong></td>
            <td>${classBadge}</td>
            <td>${statusBadge}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="openReviewModal('${lead.id}')">
                    <i class="fa-solid fa-eye"></i> Duyệt
                </button>
            </td>
        `;
        leadsTbody.appendChild(tr);
    });
    
    renderPagination();
}

function renderPagination() {
    paginationControls.innerHTML = "";
    const totalPages = Math.ceil(filteredLeads.length / itemsPerPage);
    if (totalPages <= 1) return;
    
    const prevBtn = document.createElement("button");
    prevBtn.className = "page-btn";
    prevBtn.innerHTML = '<i class="fa-solid fa-chevron-left"></i>';
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener("click", () => {
        currentPage--;
        renderLeadsTable();
    });
    paginationControls.appendChild(prevBtn);
    
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            const pageBtn = document.createElement("button");
            pageBtn.className = `page-btn ${currentPage === i ? 'active' : ''}`;
            pageBtn.innerText = i;
            pageBtn.addEventListener("click", () => {
                currentPage = i;
                renderLeadsTable();
            });
            paginationControls.appendChild(pageBtn);
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            const dots = document.createElement("span");
            dots.innerText = "...";
            dots.style.margin = "0 0.5rem";
            paginationControls.appendChild(dots);
        }
    }
    
    const nextBtn = document.createElement("button");
    nextBtn.className = "page-btn";
    nextBtn.innerHTML = '<i class="fa-solid fa-chevron-right"></i>';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.addEventListener("click", () => {
        currentPage++;
        renderLeadsTable();
    });
    paginationControls.appendChild(nextBtn);
}

// Search & Filter Actions
function applyFilters() {
    const query = searchInput.value.toLowerCase().trim();
    const classVal = filterClassification.value;
    const statusVal = filterStatus.value;
    
    filteredLeads = allLeads.filter(lead => {
        const matchesSearch = lead.ten_khach.toLowerCase().includes(query) || 
                              lead.sdt.includes(query) || 
                              lead.nhu_cau_mo_ta.toLowerCase().includes(query);
                              
        const matchesClass = !classVal ? true : 
                            (classVal === "Chưa chấm" ? lead.score === null : lead.classification === classVal);
                            
        const matchesStatus = !statusVal ? true : lead.status === statusVal;
        
        return matchesSearch && matchesClass && matchesStatus;
    });
    
    currentPage = 1;
    renderLeadsTable();
}

searchInput.addEventListener("input", applyFilters);
filterClassification.addEventListener("change", applyFilters);
filterStatus.addEventListener("change", applyFilters);

// Batch Scoring
async function scoreSingleLead(lead) {
    if (!geminiKey) {
        throw new Error("Vui lòng thiết lập Gemini API Key trước.");
    }
    
    const res = await fetch("/api/score", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Gemini-Key": geminiKey
        },
        body: JSON.stringify({
            lead_id: lead.id,
            nhu_cau_mo_ta: lead.nhu_cau_mo_ta
        })
    });
    
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Lỗi khi chấm điểm ID ${lead.id}`);
    }
    
    return await res.json();
}

async function runBatchScoring() {
    const un-scored = allLeads.filter(l => l.score === null);
    if (un-scored.length === 0) {
        showToast("Tất cả khách hàng đã được chấm điểm!");
        return;
    }
    
    if (!geminiKey) {
        showToast("Vui lòng cung cấp Gemini API Key trong Cài đặt.", "error");
        switchView("settings");
        return;
    }
    
    isScoringAll = true;
    stopScoringRequested = false;
    btnRunAllScoring.style.display = "none";
    btnStopScoring.style.display = "inline-flex";
    
    let successCount = 0;
    for (let i = 0; i < un-scored.length; i++) {
        if (stopScoringRequested) {
            showToast("Đã dừng chấm điểm hàng loạt.");
            break;
        }
        
        const lead = un-scored[i];
        try {
            const result = await scoreSingleLead(lead);
            // update in local state
            const orig = allLeads.find(l => l.id === lead.id);
            if (orig) {
                Object.assign(orig, result);
            }
            successCount++;
            updateStats();
        } catch (e) {
            console.error(e);
            showToast(e.message, "error");
            // Stop if key is invalid
            if (e.message.includes("Key") || e.message.includes("API")) {
                break;
            }
        }
        // Small delay to avoid aggressive rate limit issues
        await new Promise(r => setTimeout(r, 600));
    }
    
    isScoringAll = false;
    btnRunAllScoring.style.display = "inline-flex";
    btnStopScoring.style.display = "none";
    applyFilters();
}

btnRunAllScoring.addEventListener("click", runBatchScoring);
btnStopScoring.addEventListener("click", () => {
    stopScoringRequested = true;
});

// Export to Excel
async function exportToExcel() {
    try {
        const res = await fetch("/api/export", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(allLeads)
        });
        
        if (!res.ok) throw new Error("Không thể xuất file Excel.");
        
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "bao_cao_leads_real_estate.xlsx";
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast("Đã xuất và tải báo cáo Excel thành công!");
    } catch (e) {
        showToast(e.message, "error");
    }
}

btnExportExcel.addEventListener("click", exportToExcel);

// Human in the Loop Modal Setup
window.openReviewModal = function(id) {
    const lead = allLeads.find(l => l.id === id);
    if (!lead) return;
    
    activeLeadId = id;
    modalName.innerText = lead.ten_khach;
    modalPhone.innerText = lead.sdt;
    modalDesc.innerText = lead.nhu_cau_mo_ta;
    
    modalScore.innerText = lead.score !== null ? lead.score : "-";
    modalClass.innerText = lead.classification || "Chưa chấm điểm";
    
    // Extracted fields
    modalPositives.innerText = lead.matched_positive_criteria && lead.matched_positive_criteria.length ? lead.matched_positive_criteria.join(", ") : "-";
    modalNegatives.innerText = lead.matched_negative_criteria && lead.matched_negative_criteria.length ? lead.matched_negative_criteria.join(", ") : "-";
    
    modalBudget.innerText = lead.budget || "-";
    modalType.innerText = lead.property_type || "-";
    modalLocation.innerText = lead.location || "-";
    modalUrgency.innerText = lead.urgency || "-";
    modalExplanation.innerText = lead.explanation || "Chưa có thông tin phân tích từ AI. Vui lòng chạy chấm điểm.";
    
    adjustScore.value = lead.score !== null ? lead.score : 50;
    adjustClass.value = lead.classification || "Trung bình";
    
    // Reset status buttons selection
    const statusButtons = statusBtnGroup.querySelectorAll(".btn-status");
    statusButtons.forEach(btn => {
        btn.classList.remove("active");
        if (btn.getAttribute("data-status") === lead.status) {
            btn.classList.add("active");
        }
    });
    
    reviewModal.style.display = "flex";
};

// Handle status buttons in Modal
statusBtnGroup.querySelectorAll(".btn-status").forEach(btn => {
    btn.addEventListener("click", () => {
        statusBtnGroup.querySelectorAll(".btn-status").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
    });
});

// Modal close
function closeModal() {
    reviewModal.style.display = "none";
    activeLeadId = null;
}

btnCloseModal.addEventListener("click", closeModal);
btnModalCancel.addEventListener("click", closeModal);

// Save Modal edits
btnModalSave.addEventListener("click", async () => {
    if (!activeLeadId) return;
    
    const lead = allLeads.find(l => l.id === activeLeadId);
    if (!lead) return;
    
    const selectedStatus = statusBtnGroup.querySelector(".btn-status.active").getAttribute("data-status");
    const newScore = parseInt(adjustScore.value);
    const newClass = adjustClass.value;
    
    try {
        const res = await fetch("/api/update_lead", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                lead_id: activeLeadId,
                status: selectedStatus,
                score: newScore,
                classification: newClass
            })
        });
        
        if (!res.ok) throw new Error("Không thể cập nhật kết quả duyệt.");
        
        lead.status = selectedStatus;
        lead.score = newScore;
        lead.classification = newClass;
        
        updateStats();
        renderLeadsTable();
        closeModal();
        showToast("Đã cập nhật trạng thái khách hàng thành công!");
    } catch (e) {
        showToast(e.message, "error");
    }
});

// Initial Load
fetchLeads();
