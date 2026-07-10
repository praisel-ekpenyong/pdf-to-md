/**
 * PDF → Markdown — home page
 * Stage 1: hero dropzone. Stage 2: file strip + Convert + progress.
 * On success, stashes the job_id and navigates to /output.
 */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const DEFAULTS = {
    lang: "eng",
    ocrDpi: "300",
    minChars: "20",
    forceOcr: "false",
  };

  const SCAN_HELP =
    "Scanned or image-based pages require a one-time OCR setup on this machine. " +
    "Use Docker Compose, or install Tesseract and Poppler. Text-based PDFs convert without these tools.";

  const els = {
    sprout: $("sprout"),
    sproutBar: $("sprout-bar"),
    dropzone: $("dropzone"),
    fileInput: $("file-input"),
    btnClear: $("btn-clear"),
    btnConvert: $("btn-convert"),
    fileName: $("file-name"),
    fileSize: $("file-size"),
    progressWrap: $("progress-wrap"),
    progress: $("progress"),
    progressPct: $("progress-pct"),
    progressBar: $("progress-bar"),
    statusPill: $("status-pill"),
    healthBanner: $("health-banner"),
    error: $("error"),
    warnings: $("warnings"),
    hero: $("hero"),
    work: $("work"),
    facts: $("facts"),
    factPages: $("fact-pages"),
    factOcr: $("fact-ocr"),
    factSource: $("fact-source"),
    resultLink: $("result-link"),
    uploadLimit: $("upload-limit"),
  };

  let selectedFile = null;
  let pollTimer = null;
  let lastJobId = null;
  let maxUploadMb = 25;

  /* ----- helpers --------------------------------------------------------- */

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "\u0026amp;")
      .replace(/</g, "\u0026lt;")
      .replace(/>/g, "\u0026gt;")
      .replace(/"/g, "\u0026quot;");
  }

  function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  function setSprout(state, width) {
    if (!els.sprout) return;
    els.sprout.dataset.state = state;
    if (typeof width === "number" && els.sproutBar) els.sproutBar.style.width = `${width}%`;
  }

  /* ----- status ---------------------------------------------------------- */

  function setStatus(kind, label, title) {
    if (!els.statusPill) return;
    els.statusPill.className = `status status-${kind}`;
    const labelEl = els.statusPill.querySelector(".status-label");
    if (labelEl) labelEl.textContent = label;
    els.statusPill.title = title || label;
  }

  function setError(msg) {
    if (!els.error) return;
    if (!msg) {
      els.error.hidden = true;
      els.error.textContent = "";
      return;
    }
    els.error.hidden = false;
    els.error.textContent = msg;
  }

  function humanizeWarnings(list) {
    if (!list || !list.length) return [];
    const out = [];
    const joined = list.join(" ").toLowerCase();
    if (/tesseract|poppler|ocr|pdftoppm|scanned|no text (recovered|extracted)/.test(joined)) {
      out.push(
        "Some pages could not be fully extracted. They may be scanned or image-based. " +
          "Text-based pages were converted successfully."
      );
    }
    if (/large pdf|many pages|cpu\/ram/.test(joined)) {
      out.push("This document is large. Conversion may take several minutes.");
    }
    return out.slice(0, 2);
  }

  function setWarnings(list, { showScanHelp = false } = {}) {
    if (!els.warnings) return;
    const friendly = humanizeWarnings(list);
    const needsHelp =
      showScanHelp ||
      (list && list.some((w) => /tesseract|poppler|ocr|pdftoppm|scan/i.test(String(w))));

    if (!friendly.length && !needsHelp) {
      els.warnings.hidden = true;
      els.warnings.innerHTML = "";
      return;
    }

    let html = "";
    if (friendly.length) {
      html += "<ul>" + friendly.map((w) => `<li>${escapeHtml(w)}</li>`).join("") + "</ul>";
    }
    if (needsHelp) {
      html +=
        `<details class="warn-help">` +
        `<summary>Enable OCR for scanned documents</summary>` +
        `<p class="help-body">${escapeHtml(SCAN_HELP)}</p>` +
        `</details>`;
    }

    els.warnings.hidden = false;
    els.warnings.innerHTML = html;
  }

  /* ----- facts ----------------------------------------------------------- */

  function setFacts({ pages, ocrPages, source } = {}) {
    if (pages == null && ocrPages == null && !source) {
      if (els.facts) els.facts.hidden = true;
      return;
    }
    if (els.facts) els.facts.hidden = false;
    if (pages != null && els.factPages) els.factPages.textContent = String(pages);
    if (ocrPages != null && els.factOcr) {
      const arr = Array.isArray(ocrPages) ? ocrPages : [];
      els.factOcr.textContent = arr.length ? arr.join(", ") : "—";
    }
    if (source && els.factSource) els.factSource.textContent = source;
  }

  /* ----- busy / progress ------------------------------------------------- */

  function setBusy(busy) {
    if (!busy) {
      if (pollTimer) {
        clearTimeout(pollTimer);
        pollTimer = null;
      }
      if (els.progressWrap) els.progressWrap.hidden = true;
      setSprout("done", 100);
      window.setTimeout(() => setSprout("off", 0), 600);
    } else {
      if (els.progressWrap) els.progressWrap.hidden = false;
      setSprout("on", 4);
    }
    if (els.btnConvert) {
      els.btnConvert.disabled = busy || !selectedFile;
      els.btnConvert.setAttribute("aria-busy", busy ? "true" : "false");
    }
    if (els.btnClear) els.btnClear.disabled = busy;
    const label = els.btnConvert && els.btnConvert.querySelector(".btn-label");
    if (label) label.textContent = busy ? "Converting…" : "Convert";
  }

  function setProgress(pct, message) {
    if (els.progressWrap) els.progressWrap.hidden = false;
    const p = Math.max(0, Math.min(100, pct || 0));
    if (els.progressBar) els.progressBar.style.width = `${p}%`;
    setSprout("on", p);
    const track = els.progressWrap && els.progressWrap.querySelector(".progress-track");
    if (track) track.setAttribute("aria-valuenow", String(Math.round(p)));
    let msg = message || "Processing…";
    if (/ocr page/i.test(msg)) msg = msg.replace(/OCR page/i, "Processing page");
    if (/queued/i.test(msg)) msg = "Queued…";
    if (/starting conversion/i.test(msg)) msg = "Starting conversion…";
    if (/extracting digital/i.test(msg)) msg = "Extracting text…";
    if (/uploading/i.test(msg)) msg = "Uploading…";
    if (/complete/i.test(msg)) msg = "Complete";
    if (els.progress) els.progress.textContent = msg;
    if (els.progressPct) els.progressPct.textContent = `${Math.round(p)}%`;
  }

  function setResultLink(visible, jobId) {
    if (!els.resultLink) return;
    els.resultLink.hidden = !visible;
    if (visible && jobId) {
      els.resultLink.href = `/output?job=${encodeURIComponent(jobId)}`;
    } else if (!visible) {
      els.resultLink.href = "/output";
    }
  }

  function setUploadLimitLabel(mb) {
    maxUploadMb = mb || 25;
    if (els.uploadLimit) {
      els.uploadLimit.textContent = `PDF up to ${maxUploadMb} MB · processed locally`;
    }
  }

  /* ----- stage switching ------------------------------------------------- */

  function showStage(stage) {
    if (stage === "work") {
      if (els.hero) els.hero.hidden = true;
      if (els.work) els.work.hidden = false;
    } else {
      if (els.hero) els.hero.hidden = false;
      if (els.work) els.work.hidden = true;
    }
  }

  /* ----- file handling --------------------------------------------------- */

  function clearFile(e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    selectedFile = null;
    lastJobId = null;
    if (els.fileInput) els.fileInput.value = "";
    setError("");
    setWarnings([]);
    setFacts({});
    setResultLink(false);
    if (els.progressWrap) els.progressWrap.hidden = true;
    setSprout("off", 0);
    showStage("hero");
    if (els.dropzone) els.dropzone.focus();
  }

  function setFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select a PDF file.");
      return;
    }
    selectedFile = file;
    if (els.fileName) els.fileName.textContent = file.name;
    if (els.fileSize) els.fileSize.textContent = formatSize(file.size);
    setFacts({ source: file.name, pages: null, ocrPages: null });
    if (els.factPages) els.factPages.textContent = "—";
    if (els.factOcr) els.factOcr.textContent = "—";
    setError("");
    setWarnings([]);
    setResultLink(false);
    if (els.progressWrap) els.progressWrap.hidden = true;
    if (els.btnConvert) els.btnConvert.disabled = false;
    showStage("work");
  }

  function buildFormData() {
    const fd = new FormData();
    fd.append("file", selectedFile, selectedFile.name);
    fd.append("lang", DEFAULTS.lang);
    fd.append("force_ocr", DEFAULTS.forceOcr);
    fd.append("ocr_dpi", DEFAULTS.ocrDpi);
    fd.append("min_chars", DEFAULTS.minChars);
    return fd;
  }

  /* ----- health ---------------------------------------------------------- */

  async function refreshHealth() {
    try {
      const res = await fetch("/health");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const dig = !!data.digital_extract_available;
      const ocr = !!data.ocr_ready;
      if (typeof data.max_upload_mb === "number" && data.max_upload_mb > 0) {
        setUploadLimitLabel(data.max_upload_mb);
      } else {
        setUploadLimitLabel(25);
      }

      if (dig && ocr) {
        setStatus("ok", "Ready", "Ready to convert");
        renderHealthBanner();
      } else if (dig) {
        // Text extraction works; no OCR banner (status pill is enough).
        setStatus("ok", "Ready · text PDFs", "Text-based PDFs are supported; scanned documents require OCR setup");
        renderHealthBanner();
      } else {
        setStatus("warn", "Unavailable", "Conversion service is limited");
        renderHealthBanner({
          kind: "err",
          strong: "Conversion is not fully available.",
          hint: "Verify that the application is installed correctly.",
        });
      }
    } catch {
      setStatus("err", "Offline", "Unable to reach the server");
      renderHealthBanner({
        kind: "err",
        strong: "Unable to connect to the server.",
        hint: "Start the application and refresh this page.",
      });
    }
  }

  function renderHealthBanner(opts) {
    if (!els.healthBanner) return;
    // Accept null/undefined — do not destructure null (throws TypeError → false Offline).
    const { kind, strong, hint } = opts || {};
    if (!strong) {
      els.healthBanner.hidden = true;
      els.healthBanner.innerHTML = "";
      return;
    }
    els.healthBanner.hidden = false;
    const inner = document.createElement("div");
    inner.className = "alert-inner " + (kind || "");
    inner.innerHTML =
      `<strong>${escapeHtml(strong)}</strong>` +
      (hint ? `<span class="hint-line">${escapeHtml(hint)}</span>` : "");
    els.healthBanner.innerHTML = "";
    els.healthBanner.appendChild(inner);
  }

  /* ----- progress success: stash & navigate ------------------------------ */

  function openOutput(jobId) {
    try {
      sessionStorage.setItem("pdfmd:job_id", jobId);
    } catch {
      // sessionStorage may be unavailable; fall back to URL param below.
    }
    window.location.href = `/output?job=${encodeURIComponent(jobId)}`;
  }

  function sleep(ms) {
    return new Promise((r) => {
      pollTimer = setTimeout(r, ms);
    });
  }

  async function pollJob(jobId) {
    const maxMs = 30 * 60 * 1000;
    const start = Date.now();
    let delay = 500;

    while (Date.now() - start < maxMs) {
      const res = await fetch(`/jobs/${jobId}`);
      let body;
      try {
        body = await res.json();
      } catch {
        throw new Error("An unexpected error occurred. Please try again.");
      }
      if (!res.ok) {
        const detail = typeof body.detail === "string" ? body.detail : "Conversion failed.";
        throw new Error(detail);
      }

      setProgress(body.progress || 0, body.message || "Processing…");
      lastJobId = jobId;

      if (body.status === "completed") {
        setProgress(100, "Complete");
        setFacts({
          pages: body.page_count,
          ocrPages: body.ocr_pages,
          source: body.source_name || (selectedFile && selectedFile.name) || "",
        });
        setResultLink(true, jobId);
        setBusy(false);
        // Small delay so the user sees the "done" state before navigating.
        setTimeout(() => openOutput(jobId), 600);
        return;
      }
      if (body.status === "failed") {
        throw new Error(body.error || "Conversion failed.");
      }

      await sleep(delay);
      delay = Math.min(delay * 1.25, 2500);
    }
    throw new Error("Conversion exceeded the time limit. Try a smaller document.");
  }

  async function convert() {
    if (!selectedFile) return;
    setBusy(true);
    setError("");
    setWarnings([]);
    setResultLink(false);
    setFacts({ source: selectedFile.name });
    setProgress(4, "Uploading…");

    try {
      const res = await fetch("/jobs", {
        method: "POST",
        body: buildFormData(),
      });
      let body;
      try {
        body = await res.json();
      } catch {
        body = { detail: "Upload failed." };
      }
      if (!res.ok) {
        const detail = typeof body.detail === "string" ? body.detail : "Unable to start conversion.";
        throw new Error(detail);
      }
      setProgress(8, "Queued…");
      await pollJob(body.job_id);
    } catch (err) {
      setError(String(err.message || err));
      if (els.progressWrap) els.progressWrap.hidden = true;
      setSprout("off", 0);
      setBusy(false);
    }
  }

  /* ----- events ---------------------------------------------------------- */

  if (els.dropzone) {
    els.dropzone.addEventListener("click", () => {
      if (selectedFile) return;
      els.fileInput.click();
    });
    els.dropzone.addEventListener("keydown", (e) => {
      if ((e.key === "Enter" || e.key === " ") && !selectedFile) {
        e.preventDefault();
        els.fileInput.click();
      }
    });
  }

  if (els.fileInput) {
    els.fileInput.addEventListener("change", () => {
      if (els.fileInput.files && els.fileInput.files[0]) setFile(els.fileInput.files[0]);
    });
  }

  if (els.btnClear) els.btnClear.addEventListener("click", clearFile);
  if (els.btnConvert) els.btnConvert.addEventListener("click", convert);

  ["dragenter", "dragover"].forEach((ev) => {
    els.dropzone && els.dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (!selectedFile) els.dropzone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach((ev) => {
    els.dropzone && els.dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      els.dropzone.classList.remove("dragover");
    });
  });
  if (els.dropzone) {
    els.dropzone.addEventListener("drop", (e) => {
      const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) setFile(file);
    });
  }

  if (els.resultLink) {
    els.resultLink.addEventListener("click", (e) => {
      if (lastJobId) {
        e.preventDefault();
        openOutput(lastJobId);
      }
    });
  }

  /* ----- init ----------------------------------------------------------- */

  showStage("hero");
  setSprout("off", 0);
  setUploadLimitLabel(25);
  if (els.btnConvert) els.btnConvert.disabled = true;
  refreshHealth();
})();
