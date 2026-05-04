// =====================================================================
// Ledger — Deal Analysis · Frontend JavaScript
// Handles landing/results toggle, tabs, file inputs, API calls,
// results rendering, memo download, and follow-up chat.
// Strips stray markdown from model responses so the UI stays clean.
// =====================================================================

// ----- State -----
let currentTab = "text";
let analysisResult = null;
let chatHistory = [];

// ----- Helpers -----
const $ = (id) => document.getElementById(id);

/**
 * Scrub any stray markdown the model might produce so text displays cleanly.
 */
function stripMarkdown(text) {
  if (!text) return "";
  let out = text;
  out = out.replace(/\*\*(.+?)\*\*/g, "$1");
  out = out.replace(/__(.+?)__/g, "$1");
  out = out.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "$1");
  out = out.replace(/(?<!_)_(?!_)(.+?)(?<!_)_(?!_)/g, "$1");
  out = out.replace(/^\s*[\*\-]\s+/gm, "• ");
  out = out.replace(/^#{1,6}\s*/gm, "");
  out = out.replace(/\n{3,}/g, "\n\n");
  return out.trim();
}

function setStatus(label) {
  const pill = $("status-pill");
  if (pill) {
    pill.innerHTML = `<span class="meta-k">Status</span> ${label}`;
  }
}

// =====================================================================
// TAB SWITCHING
// =====================================================================
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const target = tab.dataset.tab;
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    tab.classList.add("active");
    document.querySelector(`[data-content="${target}"]`).classList.add("active");
    currentTab = target;
  });
});

// =====================================================================
// FILE UPLOAD HANDLERS
// =====================================================================
$("pdf-file").addEventListener("change", (e) => {
  const file = e.target.files[0];
  $("pdf-name").textContent = file ? file.name : "";
});

$("ss-file").addEventListener("change", (e) => {
  const file = e.target.files[0];
  $("ss-name").textContent = file ? file.name : "";
});

// =====================================================================
// SAMPLE DATA LOADER
// =====================================================================
$("example-btn").addEventListener("click", () => {
  document.querySelector('[data-tab="text"]').click();
  $("text-input").value = `NORTHWIND COMPONENTS CORP — Consolidated Financial Statements (USD, in millions)

INCOME STATEMENT                    FY2024      FY2023
Revenue                              2,847       2,512
Cost of Revenue                      1,623       1,445
Gross Profit                         1,224       1,067
Operating Expenses                     742         681
Operating Income                       482         386
Interest Expense                        58          52
Net Income                             318         247

BALANCE SHEET                       FY2024      FY2023
Current Assets                       1,156         998
  Inventory                            387         342
Total Assets                         3,894       3,521
Current Liabilities                    812         734
Total Liabilities                    1,987       1,842
Total Equity                         1,907       1,679

CASH FLOW STATEMENT                 FY2024      FY2023
Operating Cash Flow                    421         358
Investing Cash Flow                   (187)       (156)
Financing Cash Flow                   (124)        (98)
Capital Expenditures                  (172)       (145)`;
});

// =====================================================================
// ANALYZE BUTTON
// =====================================================================
$("analyze-btn").addEventListener("click", async () => {
  hideElement("error");

  const formData = new FormData();
  formData.append("input_type", currentTab);

  if (currentTab === "text") {
    const text = $("text-input").value.trim();
    if (!text) { showError("Please paste financial data first."); return; }
    formData.append("text", text);
  } else if (currentTab === "pdf") {
    const file = $("pdf-file").files[0];
    if (!file) { showError("Please select a PDF file."); return; }
    formData.append("file", file);
  } else if (currentTab === "spreadsheet") {
    const file = $("ss-file").files[0];
    if (!file) { showError("Please select a spreadsheet."); return; }
    formData.append("file", file);
  }

  // Transition: hide landing, show loading
  hideElement("landing");
  showLoading();
  setStatus("Analyzing");

  const messages = [
    "Extracting line items",
    "Calculating ratios in Python",
    "Generating analyst narrative",
  ];
  let msgIdx = 0;
  $("loading-text").textContent = messages[0];
  const loadingInterval = setInterval(() => {
    msgIdx = (msgIdx + 1) % messages.length;
    $("loading-text").textContent = messages[msgIdx];
  }, 2400);

  $("analyze-btn").disabled = true;

  try {
    const response = await fetch("/analyze", { method: "POST", body: formData });
    const data = await response.json();

    clearInterval(loadingInterval);
    hideElement("loading");
    $("analyze-btn").disabled = false;

    if (!response.ok) {
      // Bring landing back so the user can retry
      showElement("landing");
      setStatus("Error");
      showError(data.error || "Unknown error occurred.");
      return;
    }

    renderResults(data);
    setStatus("Analysis Complete");
  } catch (err) {
    clearInterval(loadingInterval);
    hideElement("loading");
    showElement("landing");
    $("analyze-btn").disabled = false;
    setStatus("Error");
    showError("Network error: " + err.message);
  }
});

// =====================================================================
// NEW ANALYSIS BUTTON
// =====================================================================
document.addEventListener("click", (e) => {
  if (e.target && e.target.id === "new-analysis") {
    hideElement("results");
    showElement("landing");
    analysisResult = null;
    chatHistory = [];
    $("chat-history").innerHTML = "";
    setStatus("Ready");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
});

// =====================================================================
// RENDER RESULTS
// =====================================================================
function renderResults(data) {
  const { extracted_data, calculated_ratios, trends, narrative } = data;

  analysisResult = data;
  chatHistory = [];
  $("chat-history").innerHTML = "";

  // Memo header
  $("company-name").textContent = extracted_data.company_name || "Subject Target";
  const periods = extracted_data.periods || [];
  $("period-count").textContent = periods.length.toString();
  $("currency").textContent = extracted_data.currency || "—";

  // Summary
  $("summary-text").textContent = narrative.summary || "—";

  // Trends
  if (trends && Object.keys(trends).length > 0 && trends.revenue_growth !== undefined) {
    $("trends-block").classList.remove("hidden");
    renderTrends(trends, narrative.trend_commentary);
  } else {
    $("trends-block").classList.add("hidden");
  }

  // Ratios
  renderRatios(periods, calculated_ratios);

  // Lists
  renderBulletList("strengths-list", narrative.strengths);
  renderBulletList("concerns-list", narrative.concerns);
  renderBulletList("flags-list", narrative.red_flags, "No material risks identified at this stage.");

  showElement("results");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderTrends(trends, commentary) {
  const grid = $("trends-grid");
  grid.innerHTML = "";

  const items = [
    { label: "Revenue Growth",         value: trends.revenue_growth },
    { label: "Net Income Growth",      value: trends.net_income_growth },
    { label: "Operating Income Growth", value: trends.operating_income_growth },
  ];

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "trend-card";

    let valueHtml = '<span class="trend-value neutral">—</span>';
    if (item.value !== null && item.value !== undefined) {
      const pct = (item.value * 100).toFixed(1);
      const cls = item.value > 0 ? "positive" : item.value < 0 ? "negative" : "neutral";
      const arrow = item.value > 0 ? "▲" : item.value < 0 ? "▼" : "—";
      valueHtml = `<span class="trend-value ${cls}"><span class="trend-arrow">${arrow}</span>${pct}%</span>`;
    }

    card.innerHTML = `<div class="trend-label">${item.label}</div>${valueHtml}`;
    grid.appendChild(card);
  });

  const cleanCommentary = stripMarkdown(commentary || "");
  $("trend-commentary").textContent = cleanCommentary;
  $("trend-commentary").style.display = cleanCommentary ? "block" : "none";
}

function renderRatios(periods, allRatios) {
  const container = $("ratios-container");
  container.innerHTML = "";

  periods.forEach((period, idx) => {
    const ratios = allRatios[idx];
    const table = document.createElement("table");
    table.className = "ratios-table";
    table.innerHTML = `
      <caption>${period.period_label || `Period ${idx + 1}`}</caption>
      <thead>
        <tr>
          <th>Ratio</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        ${ratioRow("Liquidity",     "Current Ratio",    ratios.liquidity.current_ratio,         "x")}
        ${ratioRow("Liquidity",     "Quick Ratio",      ratios.liquidity.quick_ratio,           "x")}
        ${ratioRow("Profitability", "Gross Margin",     ratios.profitability.gross_margin,      "%")}
        ${ratioRow("Profitability", "Operating Margin", ratios.profitability.operating_margin,  "%")}
        ${ratioRow("Profitability", "Net Margin",       ratios.profitability.net_margin,        "%")}
        ${ratioRow("Profitability", "Return on Assets", ratios.profitability.return_on_assets,  "%")}
        ${ratioRow("Profitability", "Return on Equity", ratios.profitability.return_on_equity,  "%")}
        ${ratioRow("Leverage",      "Debt-to-Equity",   ratios.leverage.debt_to_equity,         "x")}
        ${ratioRow("Leverage",      "Debt-to-Assets",   ratios.leverage.debt_to_assets,         "x")}
        ${ratioRow("Leverage",      "Interest Coverage",ratios.leverage.interest_coverage,      "x")}
        ${ratioRow("Efficiency",    "Asset Turnover",   ratios.efficiency.asset_turnover,       "x")}
      </tbody>
    `;
    container.appendChild(table);
  });
}

function ratioRow(category, name, value, format) {
  let displayed;
  if (value === null || value === undefined) {
    displayed = '<span class="ratio-value na">N/A</span>';
  } else if (format === "%") {
    displayed = `<span class="ratio-value">${(value * 100).toFixed(2)}%</span>`;
  } else {
    displayed = `<span class="ratio-value">${value.toFixed(2)}x</span>`;
  }
  return `
    <tr>
      <td>
        <span class="ratio-cat">${category}</span>
        <span class="ratio-name">${name}</span>
      </td>
      <td>${displayed}</td>
    </tr>
  `;
}

function renderBulletList(elementId, items, emptyText = "None identified.") {
  const list = $(elementId);
  list.innerHTML = "";
  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = emptyText;
    list.appendChild(li);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = stripMarkdown(item);
    list.appendChild(li);
  });
}

// =====================================================================
// MEMO DOWNLOADS
// =====================================================================
$("download-docx").addEventListener("click", () => downloadMemo("docx"));
$("download-pdf").addEventListener("click",  () => downloadMemo("pdf"));

async function downloadMemo(format) {
  if (!analysisResult) return;

  const button = $(`download-${format}`);
  const originalHtml = button.innerHTML;
  button.disabled = true;
  button.innerHTML = `<span class="dl-format">${format.toUpperCase()}</span><span class="dl-arrow">…</span>`;

  try {
    const response = await fetch(`/memo/${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(analysisResult),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      showError("Memo download failed: " + (err.error || response.statusText));
      return;
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;

    const disp = response.headers.get("Content-Disposition") || "";
    const match = disp.match(/filename="([^"]+)"/);
    a.download = match ? match[1] : `Deal_Memo.${format}`;

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (err) {
    showError("Memo download error: " + err.message);
  } finally {
    button.disabled = false;
    button.innerHTML = originalHtml;
  }
}

// =====================================================================
// CHAT
// =====================================================================
async function sendChatMessage() {
  const input = $("chat-input");
  const message = input.value.trim();
  if (!message || !analysisResult) return;

  appendChatMessage("user", message);
  chatHistory.push({ role: "user", content: message });
  input.value = "";
  $("chat-send").disabled = true;

  const placeholder = appendChatMessage("assistant", "…");

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        context: {
          extracted_data:    analysisResult.extracted_data,
          calculated_ratios: analysisResult.calculated_ratios,
          trends:            analysisResult.trends,
          narrative:         analysisResult.narrative,
        },
        conversation: chatHistory,
      }),
    });
    const data = await response.json();

    if (!response.ok) {
      placeholder.textContent = "Error: " + (data.error || "Unknown");
    } else {
      const cleanReply = stripMarkdown(data.reply);
      placeholder.textContent = cleanReply;
      chatHistory.push({ role: "assistant", content: cleanReply });
    }
  } catch (err) {
    placeholder.textContent = "Network error: " + err.message;
  }

  $("chat-send").disabled = false;
}

function appendChatMessage(role, content) {
  const div = document.createElement("div");
  div.className = `chat-message ${role}`;
  div.textContent = content;
  $("chat-history").appendChild(div);
  $("chat-history").scrollTop = $("chat-history").scrollHeight;
  return div;
}

$("chat-send").addEventListener("click", sendChatMessage);
$("chat-input").addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendChatMessage();
});

// =====================================================================
// UTILITIES
// =====================================================================
function showElement(id) { $(id).classList.remove("hidden"); }
function hideElement(id) { $(id).classList.add("hidden"); }
function showLoading()   { showElement("loading"); }
function showError(msg)  { $("error-text").textContent = msg; showElement("error"); }
