/**
 * AgriNiramaya - Frontend Application Logic & REST Client
 * Tagline: Healthy Plants. Smarter Farming.
 * EDI First-Year Engineering Project
 */

// Determine API Base URL dynamically
const getApiBase = () => {
  const { protocol, hostname, port } = window.location;

  // Production (Render): use the same origin for frontend and backend
  if (protocol === "http:" || protocol === "https:") {
    const isLocalHost = hostname === "localhost" || hostname === "127.0.0.1";

    // VS Code Live Server local development
    if (isLocalHost && port && port !== "5000") {
      return "http://127.0.0.1:5000";
    }

    return "";
  }

  // Local file testing
  return "http://127.0.0.1:5000";
};

const API_BASE = getApiBase();

// -------------------------------------------------------------
// 1. API HELPER WITH CREDENTIALS & TOKENS
// -------------------------------------------------------------
async function apiFetch(endpoint, options = {}) {
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = `${API_BASE}${cleanEndpoint}`;

  const headers = options.headers || {};
  const token = sessionStorage.getItem("agri_token");
  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const fetchOptions = {
    ...options,
    headers,
    credentials: "include" // Forward Flask session cookies
  };

  try {
    const res = await fetch(url, fetchOptions);
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    console.error(`[AgriNiramaya API Error] ${endpoint}:`, err);
    return {
      ok: false,
      status: 0,
      data: {
        success: false,
        message: "Unable to connect to AgriNiramaya backend server. Please verify Flask is running on port 5000."
      }
    };
  }
}

// -------------------------------------------------------------
// 2. TOAST NOTIFICATIONS
// -------------------------------------------------------------
function showToast(message, type = "info", duration = 3500) {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  const icons = {
    success: `<svg class="toast-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>`,
    error: `<svg class="toast-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>`,
    warning: `<svg class="toast-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>`,
    info: `<svg class="toast-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>`
  };

  toast.innerHTML = `
    ${icons[type] || icons.info}
    <div style="flex:1;">${escapeHtml(message)}</div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(20px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// -------------------------------------------------------------
// 3. AUTHENTICATION & HEADER STATE
// -------------------------------------------------------------
let currentUser = null;

async function checkAuth() {
  const { ok, data } = await apiFetch("/api/me");
  const authActionsContainer = document.getElementById("nav-auth-actions");
  
  if (ok && data.authenticated && data.user) {
    currentUser = data.user;
    sessionStorage.setItem("agri_user", JSON.stringify(data.user));

    if (authActionsContainer) {
      authActionsContainer.innerHTML = `
        <div class="user-menu-pill">
          <div class="user-avatar">${currentUser.name.charAt(0).toUpperCase()}</div>
          <span>${escapeHtml(currentUser.name)}</span>
        </div>
        <button id="logout-btn" class="btn btn-sm btn-outline" title="Log out">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/></svg>
          Logout
        </button>
      `;

      document.getElementById("logout-btn")?.addEventListener("click", handleLogout);
    }
    return currentUser;
  } else {
    currentUser = null;
    sessionStorage.removeItem("agri_user");
    sessionStorage.removeItem("agri_token");

    if (authActionsContainer) {
      authActionsContainer.innerHTML = `
        <a href="login.html" class="btn btn-sm btn-secondary">Login</a>
        <a href="signup.html" class="btn btn-sm btn-primary">Sign Up</a>
      `;
    }
    return null;
  }
}

async function handleLogout() {
  await apiFetch("/api/logout", { method: "POST" });
  sessionStorage.removeItem("agri_user");
  sessionStorage.removeItem("agri_token");
  showToast("Logged out successfully.", "info");
  setTimeout(() => {
    window.location.href = "login.html";
  }, 400);
}

function requireAuth() {
  const protectedPages = [
    "dashboard.html",
    "farm.html",
    "disease-detection.html",
    "soil-monitoring.html",
    "assistant.html",
    "history.html"
  ];

  const currentPath = window.location.pathname;
  const isProtected = protectedPages.some(page => currentPath.endsWith(page));

  if (isProtected) {
    checkAuth().then(user => {
      if (!user) {
        showToast("Please log in to access this page.", "warning");
        const returnUrl = encodeURIComponent(window.location.href);
        window.location.href = `login.html?redirect=${returnUrl}`;
      }
    });
  } else {
    checkAuth();
  }
}

// -------------------------------------------------------------
// 4. COMMON INITIALIZATION (Navbar, Mobile Toggle)
// -------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  // Mobile Nav Toggle
  const toggleBtn = document.querySelector(".mobile-nav-toggle");
  const mainNav = document.querySelector(".main-nav");
  if (toggleBtn && mainNav) {
    toggleBtn.addEventListener("click", () => {
      mainNav.classList.toggle("active");
    });
  }

  // Active Link Highlight
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll(".nav-link, .dash-subnav-item a");
  navLinks.forEach(link => {
    const href = link.getAttribute("href");
    if (href && currentPath.endsWith(href)) {
      link.classList.add("active");
    }
  });

  // Verify Auth on page load
  requireAuth();
});

// -------------------------------------------------------------
// 5. DASHBOARD PAGE CONTROLLER
// -------------------------------------------------------------
async function initDashboardPage() {
  const statsContainer = document.getElementById("dash-stats");
  const recentFarmsList = document.getElementById("recent-farms-list");
  const recentUploadsList = document.getElementById("recent-uploads-list");
  const recentActivityList = document.getElementById("recent-activity-list");
  const soilGlance = document.getElementById("dash-soil-glance");

  const { ok, data } = await apiFetch("/api/dashboard-stats");

  if (!ok) {
    showToast(data.message || "Failed to load dashboard metrics.", "error");
    return;
  }

  // Update Metric Cards (Strictly actual SQLite counts, no fake stats)
  if (document.getElementById("stat-farms-count")) {
    document.getElementById("stat-farms-count").textContent = data.stats.total_farms;
  }
  if (document.getElementById("stat-crops-count")) {
    document.getElementById("stat-crops-count").textContent = data.stats.total_crops;
  }
  if (document.getElementById("stat-scans-count")) {
    document.getElementById("stat-scans-count").textContent = data.stats.total_uploads;
  }
  if (document.getElementById("stat-soil-count")) {
    document.getElementById("stat-soil-count").textContent = data.stats.total_soil_readings;
  }

  // Recent Farms
  if (recentFarmsList) {
    if (data.recent_farms && data.recent_farms.length > 0) {
      recentFarmsList.innerHTML = data.recent_farms.map(f => `
        <div class="card" style="margin-bottom:0.75rem;">
          <div class="card-body" style="padding:1rem 1.25rem; display:flex; justify-content:space-between; align-items:center;">
            <div>
              <h4 style="color:var(--primary); font-size:1.05rem; margin-bottom:0.25rem;">${escapeHtml(f.name)}</h4>
              <p style="font-size:0.85rem; color:var(--text-muted);">${escapeHtml(f.crop_name)} • ${f.size} acres • ${escapeHtml(f.location)}</p>
            </div>
            <span class="badge badge-success">${escapeHtml(f.irrigation_method || 'Drip')}</span>
          </div>
        </div>
      `).join("");
    } else {
      recentFarmsList.innerHTML = `
        <div class="empty-state" style="padding:1.5rem;">
          <p class="empty-desc">No farms registered yet.</p>
          <a href="farm.html" class="btn btn-sm btn-primary">Add Your First Farm</a>
        </div>
      `;
    }
  }

  // Recent Leaf Scans
  if (recentUploadsList) {
    if (data.recent_uploads && data.recent_uploads.length > 0) {
      recentUploadsList.innerHTML = data.recent_uploads.map(u => `
        <div style="display:flex; align-items:center; gap:1rem; padding:0.75rem 0; border-bottom:1px solid var(--border-light);">
          <img src="${API_BASE}/api/leaf-image/${u.id}" alt="${escapeHtml(u.crop_name)}" style="width:48px; height:48px; border-radius:var(--radius-sm); object-fit:cover; border:1px solid var(--border-color);" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2248%22 height=%2248%22 viewBox=%220 0 24 24%22 fill=%22%232d6a4f%22><path d=%22M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z%22/></svg>'">
          <div style="flex:1;">
            <div style="font-weight:600; font-size:0.95rem; color:var(--primary);">${escapeHtml(u.crop_name)}</div>
            <div style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml(u.status === 'analyzed' ? u.disease_name : 'Inspection Logged')}</div>
          </div>
          <span class="badge ${u.status === 'analyzed' ? 'badge-success' : 'badge-neutral'}">${escapeHtml(u.status === 'analyzed' ? 'Analyzed' : 'Model Pending')}</span>
        </div>
      `).join("");
    } else {
      recentUploadsList.innerHTML = `
        <div class="empty-state" style="padding:1.5rem;">
          <p class="empty-desc">No plant scans uploaded yet.</p>
          <a href="disease-detection.html" class="btn btn-sm btn-secondary">Upload Plant Leaf</a>
        </div>
      `;
    }
  }

  // Soil Telemetry Glance (Rule: Display "--" if no data, never fabricate)
  if (soilGlance) {
    if (data.latest_soil) {
      const s = data.latest_soil;
      soilGlance.innerHTML = `
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:0.75rem; text-align:center;">
          <div style="background:var(--primary-surface); padding:0.85rem; border-radius:var(--radius-md);">
            <div style="font-size:0.75rem; text-transform:uppercase; color:var(--text-muted);">Moisture</div>
            <div style="font-size:1.4rem; font-weight:700; color:var(--primary);">${s.moisture}%</div>
          </div>
          <div style="background:var(--primary-surface); padding:0.85rem; border-radius:var(--radius-md);">
            <div style="font-size:0.75rem; text-transform:uppercase; color:var(--text-muted);">Temp</div>
            <div style="font-size:1.4rem; font-weight:700; color:var(--primary);">${s.temperature}°C</div>
          </div>
          <div style="background:var(--primary-surface); padding:0.85rem; border-radius:var(--radius-md);">
            <div style="font-size:0.75rem; text-transform:uppercase; color:var(--text-muted);">pH Level</div>
            <div style="font-size:1.4rem; font-weight:700; color:var(--primary);">${s.ph}</div>
          </div>
        </div>
        <div style="margin-top:0.85rem; font-size:0.85rem; color:var(--text-muted); display:flex; justify-content:space-between; align-items:center;">
          <span>Class: <strong>${escapeHtml(s.soil_classification || 'Standard')}</strong></span>
          <span>${s.is_test_data ? '<span class="badge badge-warning">Test Data</span>' : '<span class="badge badge-success">ESP32 Live</span>'}</span>
        </div>
      `;
    } else {
      soilGlance.innerHTML = `
        <div style="text-align:center; padding:1.5rem 0;">
          <p style="font-size:0.9rem; color:var(--text-muted); margin-bottom:0.75rem;">Sensor Telemetry: <strong>--</strong> (No data available)</p>
          <a href="soil-monitoring.html" class="btn btn-sm btn-secondary">Connect Node or Run Test</a>
        </div>
      `;
    }
  }

  // Recent Activity Timeline
  if (recentActivityList) {
    if (data.recent_activity && data.recent_activity.length > 0) {
      recentActivityList.innerHTML = data.recent_activity.map(a => `
        <div style="display:flex; gap:1rem; padding:0.75rem 0; border-bottom:1px solid var(--border-light);">
          <div style="width:8px; height:8px; border-radius:50%; background-color:var(--primary-accent); margin-top:0.45rem;"></div>
          <div style="flex:1;">
            <div style="font-weight:600; font-size:0.9rem; color:var(--primary);">${escapeHtml(a.title)}</div>
            <div style="font-size:0.82rem; color:var(--text-muted);">${escapeHtml(a.description)}</div>
            <div style="font-size:0.75rem; color:var(--text-light); margin-top:0.2rem;">${new Date(a.timestamp).toLocaleString()}</div>
          </div>
        </div>
      `).join("");
    } else {
      recentActivityList.innerHTML = `
        <p style="font-size:0.85rem; color:var(--text-muted); text-align:center; padding:1rem;">No recent activities logged.</p>
      `;
    }
  }
}

// -------------------------------------------------------------
// 6. FARM MANAGEMENT CONTROLLER
// -------------------------------------------------------------
let allFarms = [];

async function loadFarms() {
  const farmListContainer = document.getElementById("farm-cards-container");
  if (!farmListContainer) return;

  const { ok, data } = await apiFetch("/api/farms");
  if (!ok) {
    showToast(data.message || "Failed to load farm records.", "error");
    return;
  }

  allFarms = data.farms || [];
  renderFarmCards(allFarms);
}

function renderFarmCards(farms) {
  const container = document.getElementById("farm-cards-container");
  if (!container) return;

  if (farms.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1;">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3L2 12h3v8h14v-8h3L12 3zm0 2.84L18 11v7H6v-7l6-5.16zM9 13h6v5H9v-5z"/></svg>
        </div>
        <h3 class="empty-title">No Farms Registered</h3>
        <p class="empty-desc">Create your first agricultural parcel record to link soil monitoring and leaf disease diagnostics.</p>
        <button class="btn btn-primary" onclick="openAddFarmModal()">+ Add New Farm</button>
      </div>
    `;
    return;
  }

  container.innerHTML = farms.map(f => `
    <div class="card farm-card">
      <div class="card-header">
        <div class="card-title">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M17 12h-5v5h5v-5zM16 1v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-1V1h-2zm3 18H5V8h14v11z"/></svg>
          ${escapeHtml(f.name)}
        </div>
        <span class="badge badge-success">${escapeHtml(f.crop_name)}</span>
      </div>
      <div class="card-body">
        <div style="display:flex; flex-direction:column; gap:0.5rem; font-size:0.9rem; color:var(--text-muted);">
          <div>📍 <strong>Location:</strong> ${escapeHtml(f.location)}</div>
          <div>📐 <strong>Area:</strong> ${f.size} Acres</div>
          <div>🌾 <strong>Variety:</strong> ${escapeHtml(f.crop_variety || 'Standard')}</div>
          <div>💧 <strong>Irrigation:</strong> ${escapeHtml(f.irrigation_method || 'Drip')}</div>
          <div>🌱 <strong>Soil Type:</strong> ${escapeHtml(f.soil_type || 'Alluvial')}</div>
          ${f.field_info ? `<div style="margin-top:0.25rem; font-size:0.85rem; color:var(--text-light);"><em>${escapeHtml(f.field_info)}</em></div>` : ''}
        </div>
      </div>
      <div class="card-footer" style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:0.75rem; color:var(--text-light);">Registered: ${new Date(f.created_at).toLocaleDateString()}</span>
        <div style="display:flex; gap:0.5rem;">
          <button class="btn btn-sm btn-outline" onclick="openEditFarmModal(${f.id})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="confirmDeleteFarm(${f.id}, '${escapeHtml(f.name)}')">Delete</button>
        </div>
      </div>
    </div>
  `).join("");
}

function openAddFarmModal() {
  document.getElementById("farm-modal-title").textContent = "Add New Farm";
  document.getElementById("farm-form").reset();
  document.getElementById("farm-id-input").value = "";
  document.getElementById("farm-modal-backdrop").classList.add("active");
}

function openEditFarmModal(farmId) {
  const farm = allFarms.find(f => f.id === farmId);
  if (!farm) return;

  document.getElementById("farm-modal-title").textContent = "Edit Farm Details";
  document.getElementById("farm-id-input").value = farm.id;
  document.getElementById("farm-name-input").value = farm.name;
  document.getElementById("farm-location-input").value = farm.location;
  document.getElementById("farm-size-input").value = farm.size;
  document.getElementById("farm-crop-input").value = farm.crop_name;
  document.getElementById("farm-variety-input").value = farm.crop_variety || "";
  document.getElementById("farm-soil-input").value = farm.soil_type || "Alluvial";
  document.getElementById("farm-irrigation-input").value = farm.irrigation_method || "Drip Irrigation";
  document.getElementById("farm-notes-input").value = farm.field_info || "";

  document.getElementById("farm-modal-backdrop").classList.add("active");
}

function closeFarmModal() {
  document.getElementById("farm-modal-backdrop").classList.remove("active");
}

async function handleFarmFormSubmit(e) {
  e.preventDefault();
  const farmId = document.getElementById("farm-id-input").value;
  const payload = {
    name: document.getElementById("farm-name-input").value.trim(),
    location: document.getElementById("farm-location-input").value.trim(),
    size: parseFloat(document.getElementById("farm-size-input").value) || 1.0,
    crop_name: document.getElementById("farm-crop-input").value.trim(),
    crop_variety: document.getElementById("farm-variety-input").value.trim(),
    soil_type: document.getElementById("farm-soil-input").value,
    irrigation_method: document.getElementById("farm-irrigation-input").value,
    field_info: document.getElementById("farm-notes-input").value.trim()
  };

  const isEdit = !!farmId;
  const endpoint = isEdit ? `/api/farms/${farmId}` : "/api/farms";
  const method = isEdit ? "PUT" : "POST";

  const { ok, data } = await apiFetch(endpoint, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (ok && data.success) {
    showToast(data.message, "success");
    closeFarmModal();
    loadFarms();
  } else {
    showToast(data.message || "Failed to save farm record.", "error");
  }
}

async function confirmDeleteFarm(farmId, farmName) {
  if (confirm(`Are you sure you want to delete the farm "${farmName}"? This will also remove associated telemetry associations.`)) {
    const { ok, data } = await apiFetch(`/api/farms/${farmId}`, { method: "DELETE" });
    if (ok && data.success) {
      showToast("Farm record deleted.", "success");
      loadFarms();
    } else {
      showToast(data.message || "Failed to delete farm.", "error");
    }
  }
}

// -------------------------------------------------------------
// 7. PLANT DISEASE DETECTION CONTROLLER
// -------------------------------------------------------------
function initDiseaseDetectionPage() {
  const dropzone = document.getElementById("leaf-dropzone");
  const fileInput = document.getElementById("leaf-file-input");
  const previewBox = document.getElementById("leaf-preview-box");
  const previewImg = document.getElementById("leaf-preview-img");
  const previewFilename = document.getElementById("preview-filename");
  const uploadForm = document.getElementById("leaf-upload-form");
  const resultCard = document.getElementById("detection-result-card");
  const progressContainer = document.getElementById("upload-progress-container");

  if (!dropzone || !fileInput) return;

  // Drag and drop handlers
  ["dragenter", "dragover"].forEach(evt => {
    dropzone.addEventListener(evt, e => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(evt => {
    dropzone.addEventListener(evt, e => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", e => {
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", e => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    if (!["image/jpeg", "image/png", "image/jpg"].includes(file.type)) {
      showToast("Only JPG, JPEG, and PNG images are supported.", "error");
      fileInput.value = "";
      return;
    }

    const reader = new FileReader();
    reader.onload = e => {
      previewImg.src = e.target.result;
      previewFilename.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      previewBox.style.display = "flex";
    };
    reader.readAsDataURL(file);
  }

  // Load user's farms for linking
  loadFarmsForDropdown();
  loadUploadHistory();

  // Form submit
  uploadForm?.addEventListener("submit", async e => {
    e.preventDefault();
    if (!fileInput.files || !fileInput.files[0]) {
      showToast("Please choose or drag a plant leaf image.", "warning");
      return;
    }

    const cropName = document.getElementById("crop-name-select").value.trim();
    if (!cropName) {
      showToast("Please specify the crop name.", "warning");
      return;
    }

    const farmId = document.getElementById("farm-select-optional")?.value || "";

    const formData = new FormData();
    formData.append("crop_name", cropName);
    formData.append("image", fileInput.files[0]);
    if (farmId) formData.append("farm_id", farmId);

    // Show Progress
    if (progressContainer) progressContainer.style.display = "block";
    const submitBtn = document.getElementById("upload-submit-btn");
    if (submitBtn) submitBtn.disabled = true;

    try {
      const token = sessionStorage.getItem("agri_token");
      const headers = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/upload-leaf`, {
        method: "POST",
        headers,
        credentials: "include",
        body: formData
      });

      const data = await res.json();
      if (res.ok && data.success) {
        showToast("Leaf image analyzed successfully!", "success");
        renderDetectionResult(data.record);
        loadUploadHistory();
      } else {
        showToast(data.message || "Failed to process image.", "error");
      }
    } catch (err) {
      showToast("Upload network error.", "error");
    } finally {
      if (progressContainer) progressContainer.style.display = "none";
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

function renderDetectionResult(record) {
  const resultCard = document.getElementById("detection-result-card");
  if (!resultCard) return;

  resultCard.style.display = "block";
  resultCard.scrollIntoView({ behavior: "smooth" });

  document.getElementById("res-crop-name").textContent = record.crop_name;
  document.getElementById("res-disease-name").textContent = record.disease_name;
  
  // Rule check: Transparently display model status without fabricating fake confidence
  const confBadge = document.getElementById("res-confidence-badge");
  if (record.confidence !== null && record.confidence !== undefined) {
    confBadge.textContent = `Confidence: ${(record.confidence * 100).toFixed(1)}%`;
    confBadge.className = "badge badge-success";
  } else {
    confBadge.textContent = "Confidence: -- (Model Weights Pending)";
    confBadge.className = "badge badge-warning";
  }

  document.getElementById("res-status-text").textContent = record.status === "analyzed" ? "Analyzed with CNN Weights" : "Image Archived • Ready for CNN Weights";
  document.getElementById("res-symptoms").textContent = record.symptoms || "No symptoms recorded.";
  document.getElementById("res-info").textContent = record.disease_info || "Consult local agricultural extension advisor.";
  document.getElementById("res-care").textContent = record.care_suggestions || "Maintain drip irrigation and sanitize tools.";
  document.getElementById("res-preventive").textContent = record.preventive_measures || "Practice regular crop rotation.";
  
  const inspectedImg = document.getElementById("res-inspected-image");
  if (inspectedImg) {
    inspectedImg.src = `${API_BASE}/api/leaf-image/${record.id}`;
  }
}

async function loadFarmsForDropdown() {
  const select = document.getElementById("farm-select-optional");
  if (!select) return;

  const { ok, data } = await apiFetch("/api/farms");
  if (ok && data.farms) {
    select.innerHTML = `<option value="">-- No specific farm --</option>` +
      data.farms.map(f => `<option value="${f.id}">${escapeHtml(f.name)} (${escapeHtml(f.crop_name)})</option>`).join("");
  }
}

async function loadUploadHistory() {
  const container = document.getElementById("leaf-history-table-body");
  if (!container) return;

  const { ok, data } = await apiFetch("/api/uploads");
  if (!ok || !data.uploads || data.uploads.length === 0) {
    container.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:1.5rem; color:var(--text-muted);">No leaf inspections found.</td></tr>`;
    return;
  }

  container.innerHTML = data.uploads.map(u => `
    <tr>
      <td>
        <img src="${API_BASE}/api/leaf-image/${u.id}" alt="${escapeHtml(u.crop_name)}" style="width:40px; height:40px; border-radius:var(--radius-sm); object-fit:cover; border:1px solid var(--border-color);">
      </td>
      <td><strong>${escapeHtml(u.crop_name)}</strong><br><span style="font-size:0.75rem; color:var(--text-light);">${escapeHtml(u.original_filename)}</span></td>
      <td>${escapeHtml(u.disease_name)}</td>
      <td><span class="badge ${u.status === 'analyzed' ? 'badge-success' : 'badge-neutral'}">${escapeHtml(u.status === 'analyzed' ? 'Analyzed' : 'Pending Weights')}</span></td>
      <td>${new Date(u.created_at).toLocaleDateString()}</td>
    </tr>
  `).join("");
}

// -------------------------------------------------------------
// 8. SOIL MONITORING CONTROLLER
// -------------------------------------------------------------
async function initSoilMonitoringPage() {
  await loadLatestSoil();
  await loadSoilHistory();

  // Test data form listener
  const testForm = document.getElementById("soil-test-form");
  testForm?.addEventListener("submit", handleSoilTestSubmit);
}

async function loadLatestSoil() {
  const { ok, data } = await apiFetch("/api/latest-soil");
  const statusIndicator = document.getElementById("sensor-status-indicator");
  const statusTime = document.getElementById("sensor-status-time");

  // Rule: Display "--" or "No data available" if no sensor telemetry exists, never fabricate!
  if (!ok || !data.has_data || !data.reading) {
    document.getElementById("gauge-moisture").textContent = "--";
    document.getElementById("gauge-temp").textContent = "--";
    document.getElementById("gauge-ph").textContent = "--";
    document.getElementById("gauge-humidity").textContent = "--";
    document.getElementById("soil-classification-text").textContent = "No data available (Awaiting first reading)";
    
    if (statusIndicator) {
      statusIndicator.innerHTML = `<span class="pulse-dot offline"></span> Sensor Offline (No Telemetry Recorded)`;
    }
    if (statusTime) {
      statusTime.textContent = "Last update: Never";
    }
    return;
  }

  const r = data.reading;
  document.getElementById("gauge-moisture").textContent = `${r.moisture}%`;
  document.getElementById("gauge-temp").textContent = `${r.temperature}°C`;
  document.getElementById("gauge-ph").textContent = `${r.ph}`;
  document.getElementById("gauge-humidity").textContent = r.humidity !== null ? `${r.humidity}%` : "--";
  
  document.getElementById("soil-classification-text").textContent = r.soil_classification || "Standard Profile";

  if (statusIndicator) {
    if (r.is_test_data) {
      statusIndicator.innerHTML = `<span class="pulse-dot online" style="background-color:var(--warning);"></span> Manual Test Data Mode`;
    } else if (data.is_live) {
      statusIndicator.innerHTML = `<span class="pulse-dot online"></span> ESP32 Connected & Transmitting`;
    } else {
      statusIndicator.innerHTML = `<span class="pulse-dot offline"></span> ESP32 Standby (Telemetry Logged)`;
    }
  }

  if (statusTime) {
    statusTime.textContent = `Last update: ${new Date(r.created_at).toLocaleString()}`;
  }

  // Render Agronomic Diagnostic Advice
  const adviceContainer = document.getElementById("soil-agronomic-advice");
  if (adviceContainer && r.analysis) {
    adviceContainer.innerHTML = `
      <div class="alert alert-info" style="margin-bottom:0.75rem;">
        <div>
          <strong>💧 Irrigation Evaluation:</strong> ${escapeHtml(r.analysis.irrigation_advice)}
        </div>
      </div>
      <div class="alert alert-success" style="margin-bottom:0.75rem;">
        <div>
          <strong>🧪 pH Conditioning:</strong> ${escapeHtml(r.analysis.ph_advice)}
        </div>
      </div>
      <div class="alert alert-warning">
        <div>
          <strong>🌡️ Thermal Assessment:</strong> ${escapeHtml(r.analysis.temp_advice)}
        </div>
      </div>
    `;
  }
}

async function loadSoilHistory() {
  const container = document.getElementById("soil-history-table-body");
  if (!container) return;

  const { ok, data } = await apiFetch("/api/soil-data?limit=25");
  if (!ok || !data.readings || data.readings.length === 0) {
    container.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:1.5rem; color:var(--text-muted);">No sensor readings logged.</td></tr>`;
    return;
  }

  container.innerHTML = data.readings.map(r => `
    <tr>
      <td>${new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ${new Date(r.created_at).toLocaleDateString()}</td>
      <td><strong>${r.moisture}%</strong></td>
      <td>${r.temperature}°C</td>
      <td>${r.ph}</td>
      <td>${r.humidity !== null ? r.humidity + '%' : '--'}</td>
      <td><span class="badge ${r.is_test_data ? 'badge-warning' : 'badge-success'}">${r.is_test_data ? 'Test Data' : 'ESP32 Node'}</span></td>
      <td>${escapeHtml(r.soil_classification || 'Standard')}</td>
    </tr>
  `).join("");
}

async function handleSoilTestSubmit(e) {
  e.preventDefault();
  const moisture = parseFloat(document.getElementById("test-moisture").value);
  const temp = parseFloat(document.getElementById("test-temperature").value);
  const ph = parseFloat(document.getElementById("test-ph").value);
  const humidity = document.getElementById("test-humidity").value ? parseFloat(document.getElementById("test-humidity").value) : null;

  const payload = {
    moisture,
    temperature: temp,
    ph,
    humidity,
    device_id: "MANUAL_TEST_CONSOLE",
    is_test_data: 1 // Rule: Manual test data is clearly flagged as test data!
  };

  const { ok, data } = await apiFetch("/api/sensor-data", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (ok && data.success) {
    showToast("Test telemetry recorded successfully!", "success");
    closeTestModal();
    await loadLatestSoil();
    await loadSoilHistory();
  } else {
    showToast(data.message || "Failed to record telemetry.", "error");
  }
}

function openTestModal() {
  document.getElementById("soil-test-modal").classList.add("active");
}
function closeTestModal() {
  document.getElementById("soil-test-modal").classList.remove("active");
}

function openEsp32Modal() {
  document.getElementById("esp32-code-modal").classList.add("active");
}
function closeEsp32Modal() {
  document.getElementById("esp32-code-modal").classList.remove("active");
}

// -------------------------------------------------------------
// 9. AGRICULTURE ASSISTANT CONTROLLER
// -------------------------------------------------------------
function initAssistantPage() {
  const chatMessages = document.getElementById("chat-messages");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const topicChips = document.querySelectorAll(".topic-chip");

  if (!chatForm || !chatInput) return;

  topicChips.forEach(chip => {
    chip.addEventListener("click", () => {
      chatInput.value = chip.dataset.query || chip.textContent;
      chatInput.focus();
    });
  });

  chatForm.addEventListener("submit", async e => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    // Append User Message Bubble
    appendChatMessage("user", query, "You");
    chatInput.value = "";

    // Show Typing Indicator
    const typingBubble = document.createElement("div");
    typingBubble.className = "chat-bubble assistant";
    typingBubble.id = "chat-typing";
    typingBubble.innerHTML = `<span class="chat-bubble-source">Consulting Agronomy Engine...</span>Analyzing agricultural guidelines...`;
    chatMessages.appendChild(typingBubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    const { ok, data } = await apiFetch("/api/assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: query })
    });

    typingBubble.remove();

    if (ok && data.success && data.response) {
      appendChatMessage("assistant", data.response.answer, "AgriNiramaya Agronomist");
    } else {
      appendChatMessage("assistant", data.message || "Agricultural knowledge base currently unreachable.", "System Notice");
    }
  });

  function appendChatMessage(sender, text, label) {
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${sender}`;
    bubble.innerHTML = `
      <span class="chat-bubble-source">${escapeHtml(label)}</span>
      <div>${escapeHtml(text)}</div>
    `;
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
}

// -------------------------------------------------------------
// 10. HISTORY PAGE CONTROLLER
// -------------------------------------------------------------
async function initHistoryPage() {
  const tableBody = document.getElementById("history-records-body");
  const filterSelect = document.getElementById("history-filter-select");
  const searchInput = document.getElementById("history-search-input");

  if (!tableBody) return;

  // Fetch both uploads and soil telemetry concurrently
  const [uploadsRes, soilRes] = await Promise.all([
    apiFetch("/api/uploads"),
    apiFetch("/api/soil-data?limit=50")
  ]);

  let records = [];

  if (uploadsRes.ok && uploadsRes.data.uploads) {
    uploadsRes.data.uploads.forEach(u => {
      records.push({
        type: "leaf_scan",
        timestamp: u.created_at,
        title: `Leaf Scan: ${u.crop_name}`,
        details: `Disease: ${u.disease_name} (${u.status === 'analyzed' ? 'Analyzed' : 'Model Pending'})`,
        badgeClass: u.status === 'analyzed' ? 'badge-success' : 'badge-neutral',
        badgeText: 'Leaf Scan',
        viewUrl: `${API_BASE}/api/leaf-image/${u.id}`
      });
    });
  }

  if (soilRes.ok && soilRes.data.readings) {
    soilRes.data.readings.forEach(s => {
      records.push({
        type: "soil_reading",
        timestamp: s.created_at,
        title: `Soil Telemetry: ${s.moisture}% Moisture`,
        details: `Temp: ${s.temperature}°C • pH: ${s.ph} • Class: ${s.soil_classification || 'Standard'}`,
        badgeClass: s.is_test_data ? 'badge-warning' : 'badge-info',
        badgeText: s.is_test_data ? 'Test Data' : 'ESP32 Node',
        viewUrl: null
      });
    });
  }

  // Sort Chronologically descending
  records.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  function renderTable(filterType = "all", searchTerm = "") {
    let filtered = records;
    if (filterType !== "all") {
      filtered = filtered.filter(r => r.type === filterType);
    }
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(r => r.title.toLowerCase().includes(term) || r.details.toLowerCase().includes(term));
    }

    if (filtered.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:2rem; color:var(--text-muted);">No matching history records found.</td></tr>`;
      return;
    }

    tableBody.innerHTML = filtered.map(r => `
      <tr>
        <td style="white-space:nowrap; font-size:0.85rem; color:var(--text-muted);">${new Date(r.timestamp).toLocaleString()}</td>
        <td><span class="badge ${r.badgeClass}">${r.badgeText}</span></td>
        <td>
          <div style="font-weight:600; color:var(--primary); font-size:0.95rem;">${escapeHtml(r.title)}</div>
          <div style="font-size:0.85rem; color:var(--text-muted);">${escapeHtml(r.details)}</div>
        </td>
        <td>
          ${r.viewUrl ? `<a href="${r.viewUrl}" target="_blank" class="btn btn-sm btn-outline">View Leaf</a>` : `<span style="font-size:0.8rem; color:var(--text-light);">Telemetry Log</span>`}
        </td>
      </tr>
    `).join("");
  }

  renderTable();

  filterSelect?.addEventListener("change", e => {
    renderTable(e.target.value, searchInput?.value || "");
  });

  searchInput?.addEventListener("input", e => {
    renderTable(filterSelect?.value || "all", e.target.value);
  });
}

// -------------------------------------------------------------
// 11. CONTACT FORM CONTROLLER
// -------------------------------------------------------------
function initContactPage() {
  const form = document.getElementById("contact-form");
  if (!form) return;

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const payload = {
      name: document.getElementById("contact-name").value.trim(),
      email: document.getElementById("contact-email").value.trim(),
      subject: document.getElementById("contact-subject").value.trim(),
      message: document.getElementById("contact-message").value.trim()
    };

    const { ok, data } = await apiFetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (ok && data.success) {
      showToast(data.message, "success");
      form.reset();
    } else {
      showToast(data.message || "Failed to submit inquiry.", "error");
    }
  });
}
