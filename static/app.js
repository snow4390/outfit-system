const outfitForm = document.getElementById("outfitForm");
const textQueryInput = document.getElementById("textQuery");
const submitBtn = document.getElementById("submitBtn");

const statusBox = document.getElementById("statusBox");
const resultSection = document.getElementById("resultSection");

const topAnalysisList = document.getElementById("topAnalysisList");
const bottomAnalysisList = document.getElementById("bottomAnalysisList");
const rankedOutfitsList = document.getElementById("rankedOutfitsList");
const recommendationBox = document.getElementById("recommendationBox");

const topCountBadge = document.getElementById("topCountBadge");
const bottomCountBadge = document.getElementById("bottomCountBadge");

function setStatus(message, type = "info") {
    statusBox.textContent = message;
    statusBox.className = `status-box ${type}`;
}

function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function clearElement(el) {
    el.innerHTML = "";
}

function formatStyleTop3(styleTop3) {
    if (!styleTop3 || styleTop3.length === 0) return "無資料";
    return styleTop3
        .map((item) => `${item.label} (${item.score})`)
        .join("、");
}

function formatHSV(hsv) {
    if (!hsv || hsv.length < 3) return "無資料";
    return `H:${hsv[0]} / S:${hsv[1]} / V:${hsv[2]}`;
}

function createColorSwatches(paletteRgb) {
    if (!paletteRgb || paletteRgb.length === 0) {
        return `<span class="muted">無資料</span>`;
    }

    return paletteRgb
        .map((rgb) => {
            const color = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
            return `
                <span
                    class="swatch"
                    title="${escapeHtml(color)}"
                    style="background-color: ${color};"
                ></span>
            `;
        })
        .join("");
}

function renderAnalysisCard(item, index, typeLabel) {
    const category = item.category || "無法識別";
    const style = item.style || "無法識別";
    const fit = (item.fit && item.fit.label) ? item.fit.label : "unknown";
    const patternLabel =
        (item.pattern && item.pattern.label) ?
        item.pattern.label :
        (item.pattern && item.pattern.is_solid ? "solid" : "unknown");
    const color = item.color || {};

    return `
        <div class="analysis-card">
            <div class="analysis-card__head">
                <h5>${typeLabel} ${index + 1}</h5>
                <span class="mini-badge">${escapeHtml(category)}</span>
            </div>

            <div class="analysis-table">
                <div class="analysis-row">
                    <span class="label">主要風格</span>
                    <span class="value">${escapeHtml(style)}</span>
                </div>
                <div class="analysis-row">
                    <span class="label">Top3 風格</span>
                    <span class="value">${escapeHtml(formatStyleTop3(item.style_top3))}</span>
                </div>
                <div class="analysis-row">
                    <span class="label">版型</span>
                    <span class="value">${escapeHtml(fit)}</span>
                </div>
                <div class="analysis-row">
                    <span class="label">圖案</span>
                    <span class="value">${escapeHtml(patternLabel)}</span>
                </div>
                <div class="analysis-row">
                    <span class="label">主色 HSV</span>
                    <span class="value">${escapeHtml(formatHSV(color.main_hsv))}</span>
                </div>
                <div class="analysis-row">
                    <span class="label">色票</span>
                    <span class="value swatch-row">
                        ${createColorSwatches(color.palette_rgb)}
                    </span>
                </div>
            </div>
        </div>
    `;
}

function renderAnalysisSection(items, container, badge, typeLabel) {
    clearElement(container);

    const count = items ? items.length : 0;
    badge.textContent = `${count} 件`;

    if (!items || items.length === 0) {
        container.innerHTML = `<div class="empty-card">目前沒有${typeLabel}分析結果</div>`;
        return;
    }

    container.innerHTML = items
        .map((item, index) => renderAnalysisCard(item, index, typeLabel))
        .join("");
}

function renderBreakdown(breakdown) {
    if (!breakdown) return `<div class="muted">無資料</div>`;

    return `
        <div class="breakdown-grid">
            <div class="breakdown-item">
                <span class="breakdown-label">🎨 色彩搭配</span>
                <span class="breakdown-value">${breakdown.color ?? 0}</span>
            </div>
            <div class="breakdown-item">
                <span class="breakdown-label">👕 風格一致性</span>
                <span class="breakdown-value">${breakdown.style ?? 0}</span>
            </div>
            <div class="breakdown-item">
                <span class="breakdown-label">🧩 圖案協調度</span>
                <span class="breakdown-value">${breakdown.pattern ?? 0}</span>
            </div>
            <div class="breakdown-item">
                <span class="breakdown-label">📏 版型比例</span>
                <span class="breakdown-value">${breakdown.silhouette ?? 0}</span>
            </div>
        </div>
    `;
}

function renderMessageList(items, type) {
    if (!items || items.length === 0) {
        return `<div class="list-empty">無</div>`;
    }

    const itemClass = type === "warning" ? "warning-item" : "reason-item";

    return `
        <ul class="message-list">
            ${items.map((text) => `<li class="${itemClass}">${escapeHtml(text)}</li>`).join("")}
        </ul>
    `;
}

function renderRankedOutfitCard(outfit, index) {
    const topItem = outfit.items?.top || {};
    const bottomItem = outfit.items?.bottom || {};
    const score = outfit.score ?? 0;
    const scoreInfo = getScoreLevel(score);

    const topImage = topItem.image_path ? `/${topItem.image_path}` : "";
    const bottomImage = bottomItem.image_path ? `/${bottomItem.image_path}` : "";

    return `
        <div class="rank-card">
            <div class="rank-card__head">
                <div>
                    <p class="rank-number">TOP ${index + 1}</p>
                    <h4>${escapeHtml(topItem.category || "未知上衣")} × ${escapeHtml(bottomItem.category || "未知下裝")}</h4>
                </div>
                <div class="score-panel">
                    <div class="score-number">${score}</div>
                    <div class="score-stars">${scoreInfo.stars}</div>
                    <div class="score-level">${scoreInfo.level}</div>
                </div>
            </div>

            <div class="rank-layout">
                <div class="rank-left">
                    <div class="rank-images">
                        <div class="rank-image-card">
                            <div class="rank-image-frame">
                                <img src="${topImage}" alt="top-image">
                            </div>
                            <p class="rank-image-title">上衣</p>
                            <span class="mini-badge">${escapeHtml(topItem.category || "未知")}</span>
                        </div>

                        <div class="rank-x">×</div>

                        <div class="rank-image-card">
                            <div class="rank-image-frame">
                                <img src="${bottomImage}" alt="bottom-image">
                            </div>
                            <p class="rank-image-title">下裝</p>
                            <span class="mini-badge">${escapeHtml(bottomItem.category || "未知")}</span>
                        </div>
                    </div>
                </div>

                <div class="rank-right">
                    <div class="rank-summary">
                        <div class="rank-summary__item">
                            <span class="rank-label">上衣風格</span>
                            <span class="rank-value">${escapeHtml(topItem.style || "未知")}</span>
                        </div>
                        <div class="rank-summary__item">
                            <span class="rank-label">下裝風格</span>
                            <span class="rank-value">${escapeHtml(bottomItem.style || "未知")}</span>
                        </div>
                    </div>

                    <div class="rank-breakdown">
                        <h5>分項評分</h5>
                        ${renderBreakdown(outfit.breakdown)}
                        <div class="ai-comment">
                            ${
                                score >= 85
                                ? "這套搭配在色彩與風格上非常協調，屬於高完成度穿搭。"
                                : score >= 70
                                ? "整體搭配表現良好，可透過配件進一步提升質感。"
                                : "搭配仍有優化空間，建議調整色彩或版型比例。"
                            }
                        </div>
                    </div>

                    <div class="rank-messages two-col">
                        <div class="message-box reason-box">
                            <h5>優點</h5>
                            ${renderMessageList(outfit.reasons, "reason")}
                        </div>
                        <div class="message-box warning-box">
                            <h5>注意事項</h5>
                            ${renderMessageList(outfit.warnings, "warning")}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderRankedOutfits(outfits) {
    clearElement(rankedOutfitsList);

    if (!outfits || outfits.length === 0) {
        rankedOutfitsList.innerHTML = `<div class="empty-card">目前沒有可顯示的搭配結果</div>`;
        return;
    }

    rankedOutfitsList.innerHTML = outfits
        .map((outfit, index) => renderRankedOutfitCard(outfit, index))
        .join("");
}

function renderRecommendation(text) {
    if (!text || !text.trim()) {
        recommendationBox.innerHTML = `<div class="empty-card">目前沒有 AI 建議內容</div>`;
        return;
    }

    const formatted = escapeHtml(text).replace(/\n/g, "<br>");
    recommendationBox.innerHTML = `<div class="recommendation-text">${formatted}</div>`;
}

function showResults(data) {
    const analysis = data.analysis || {};
    renderAnalysisSection(analysis.top || [], topAnalysisList, topCountBadge, "上衣");
    renderAnalysisSection(analysis.bottom || [], bottomAnalysisList, bottomCountBadge, "下裝");
    renderRankedOutfits(data.ranked_outfits || []);
    renderRecommendation(data.recommendation || "");

    resultSection.classList.remove("hidden");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetResults() {
    resultSection.classList.add("hidden");
    clearElement(topAnalysisList);
    clearElement(bottomAnalysisList);
    clearElement(rankedOutfitsList);
    clearElement(recommendationBox);
    topCountBadge.textContent = "0 件";
    bottomCountBadge.textContent = "0 件";
}

function buildFormData() {
    const formData = new FormData();

    const topItems = document.querySelectorAll('input[name="top_item_ids"]:checked');
    const bottomItems = document.querySelectorAll('input[name="bottom_item_ids"]:checked');
    const textQuery = textQueryInput.value.trim();

    topItems.forEach((item) => {
        formData.append("top_item_ids", item.value);
    });

    bottomItems.forEach((item) => {
        formData.append("bottom_item_ids", item.value);
    });

    if (textQuery) {
        formData.append("text_query", textQuery);
    }

    return {
        formData,
        topCount: topItems.length,
        bottomCount: bottomItems.length,
        textQuery
    };
}

function validateBeforeSubmit(topCount, bottomCount, textQuery) {
    if (topCount === 0 && bottomCount === 0 && !textQuery) {
        setStatus("請至少勾選衣物，或輸入補充需求。", "error");
        return false;
    }

    return true;
}

async function submitAnalysis(event) {
    event.preventDefault();

    const { formData, topCount, bottomCount, textQuery } = buildFormData();

    if (!validateBeforeSubmit(topCount, bottomCount, textQuery)) return;

    submitBtn.disabled = true;
    submitBtn.textContent = "分析中...";
    setStatus("系統分析中，請稍候...", "loading");
    resetResults();

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "分析失敗，請稍後再試。");
        }

        setStatus("分析完成。", "success");
        showResults(data);
    } catch (error) {
        console.error("分析失敗：", error);
        setStatus(error.message || "發生未知錯誤。", "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "開始分析";
    }
}

function resetForm() {
    outfitForm.reset();
    resetResults();
    setStatus("可自由勾選衣物，或直接輸入補充需求後開始分析。", "info");
}

function getScoreLevel(score) {
    if (score >= 90) {
        return {
            level: "完美搭配",
            stars: "★★★★★"
        };
    }

    if (score >= 80) {
        return {
            level: "優秀搭配",
            stars: "★★★★☆"
        };
    }

    if (score >= 70) {
        return {
            level: "良好搭配",
            stars: "★★★☆☆"
        };
    }

    if (score >= 60) {
        return {
            level: "普通搭配",
            stars: "★★☆☆☆"
        };
    }

    return {
        level: "建議重新搭配",
        stars: "★☆☆☆☆"
    };
}

outfitForm.addEventListener("submit", submitAnalysis);

resetResults();
setStatus("可自由勾選衣物，或直接輸入補充需求後開始分析。", "info");