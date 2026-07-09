/**
 * PDF to Markdown — web UI
 * Upload → convert (async job) → copy / download
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
    dropzone: $("dropzone"),
    fileInput: $("file-input"),
    uploaderIdle: $("uploader-idle"),
    uploaderFile: $("uploader-file"),
    fileName: $("file-name"),
    fileSize: $("file-size"),
    btnClear: $("btn-clear"),
    btnConvert: $("btn-convert"),
    btnDownload: $("btn-download"),
    btnCopy: $("btn-copy"),
    output: $("output"),
    previewEmpty: $("preview-empty"),
    previewSkeleton: $("preview-skeleton"),
    meta: $("meta"),
    error: $("error"),
    progressWrap: $("progress-wrap"),
    progress: $("progress"),
    progressPct: $("progress-pct"),
    progressBar: $("progress-bar"),
    statusPill: $("status-pill"),
    healthBanner: $("health-banner"),
    warnings: $("warnings"),
    panelResult: $("panel-result"),
    resultActions: $("result-actions"),
  };

  let selectedFile = null;
  let lastMarkdown = "";
  let lastSourceName = "";
  let pollTimer = null;

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  function setStatus(kind, label, title) {
    els.statusPill.className = `status status-${kind}`;
    const labelEl = els.statusPill.querySelector(".status-label");
    if (labelEl) labelEl.textContent = label;
    els.statusPill.title = title || label;
  }

  function setError(msg) {
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
      html +=
        "<ul>" + friendly.map((w) => `<li>${escapeHtml(w)}</li>`).join("") + "</ul>";
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

  function setSkeleton(on) {
    if (!els.previewSkeleton) return;
    els.previewSkeleton.hidden = !on;
    els.previewSkeleton.setAttribute("aria-hidden", on ? "false" : "true");
  }

  function setPreviewEmpty(isEmpty) {
    els.output.classList.toggle("is-empty", isEmpty);
    if (els.previewEmpty) {
      const skeletonOn = els.previewSkeleton && !els.previewSkeleton.hidden;
      els.previewEmpty.style.display = isEmpty && !skeletonOn ? "" : "none";
    }
  }

  function setOutput(text, { empty = false } = {}) {
    els.output.textContent = empty ? "" : text;
    if (!empty) setSkeleton(false);
    setPreviewEmpty(empty);
  }

  function setResultState(state) {
    if (els.panelResult) els.panelResult.dataset.state = state;
  }

  function setResultActionsIdle(idle) {
    if (els.resultActions) els.resultActions.dataset.idle = idle ? "true" : "false";
  }

  function setMeta(pageCount) {
    if (!els.meta) return;
    if (pageCount == null) {
      els.meta.hidden = true;
      els.meta.textContent = "";
      return;
    }
    const n = pageCount;
    els.meta.textContent = `${n} page${n === 1 ? "" : "s"}`;
    els.meta.hidden = false;
  }

  function setBusy(busy) {
    if (!busy) {
      if (pollTimer) {
        clearTimeout(pollTimer);
        pollTimer = null;
      }
      if (!lastMarkdown) els.progressWrap.hidden = true;
      setSkeleton(false);
      setPreviewEmpty(!lastMarkdown);
      setResultState(lastMarkdown ? "ready" : "empty");
    } else {
      els.progressWrap.hidden = false;
      setSkeleton(true);
      if (els.previewEmpty) els.previewEmpty.style.display = "none";
      els.output.classList.add("is-empty");
      setResultState("busy");
      setMeta(null);
    }
    els.btnConvert.disabled = busy || !selectedFile;
    els.btnConvert.setAttribute("aria-busy", busy ? "true" : "false");
    els.btnDownload.disabled = busy || !lastMarkdown;
    els.btnCopy.disabled = busy || !lastMarkdown;
    setResultActionsIdle(busy || !lastMarkdown);
    if (els.btnClear) els.btnClear.disabled = busy;

    const label = els.btnConvert && els.btnConvert.querySelector(".btn-label");
    if (label) {
      label.textContent = busy ? "Converting…" : "Convert";
    }
  }

  function setProgress(pct, message) {
    els.progressWrap.hidden = false;
    const p = Math.max(0, Math.min(100, pct || 0));
    els.progressBar.style.width = `${p}%`;
    const track = els.progressWrap.querySelector(".progress-track");
    if (track) track.setAttribute("aria-valuenow", String(Math.round(p)));
    let msg = message || "Processing…";
    if (/ocr page/i.test(msg)) msg = msg.replace(/OCR page/i, "Processing page");
    if (/queued/i.test(msg)) msg = "Queued…";
    if (/starting conversion/i.test(msg)) msg = "Starting conversion…";
    if (/extracting digital/i.test(msg)) msg = "Extracting text…";
    if (/uploading/i.test(msg)) msg = "Uploading…";
    if (/complete/i.test(msg)) msg = "Complete";
    els.progress.textContent = msg;
    if (els.progressPct) els.progressPct.textContent = `${Math.round(p)}%`;
  }

  function clearFile(e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    selectedFile = null;
    els.fileInput.value = "";
    els.dropzone.classList.remove("has-file");
    els.uploaderIdle.hidden = false;
    els.uploaderFile.hidden = true;
    els.btnConvert.disabled = true;
    setError("");
    els.dropzone.focus();
  }

  function setFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select a PDF file.");
      return;
    }
    selectedFile = file;
    els.dropzone.classList.add("has-file");
    els.uploaderIdle.hidden = true;
    els.uploaderFile.hidden = false;
    els.fileName.textContent = file.name;
    els.fileSize.textContent = formatSize(file.size);
    els.btnConvert.disabled = false;
    setError("");
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

  async function refreshHealth() {
    try {
      const res = await fetch("/health");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const dig = !!data.digital_extract_available;
      const ocr = !!data.ocr_ready;

      if (dig && ocr) {
        setStatus("ok", "Ready", "Ready to convert");
        els.healthBanner.hidden = true;
      } else if (dig) {
        setStatus(
          "ok",
          "Ready · text PDFs",
          "Text-based PDFs are supported; scanned documents require OCR setup"
        );
        els.healthBanner.hidden = false;
        els.healthBanner.className = "banner warn";
        els.healthBanner.innerHTML =
          `<strong>OCR is not configured for scanned documents.</strong>` +
          `<span class="hint-line">Text-based PDFs can be converted now. Scanned pages require an additional one-time setup.</span>` +
          `<details>` +
          `<summary>Enable OCR for scanned documents</summary>` +
          `<p class="help-body">${escapeHtml(SCAN_HELP)}</p>` +
          `</details>`;
      } else {
        setStatus("warn", "Unavailable", "Conversion service is limited");
        els.healthBanner.hidden = false;
        els.healthBanner.className = "banner warn";
        els.healthBanner.textContent =
          "Conversion is not fully available. Verify that the application is installed correctly.";
      }
    } catch {
      setStatus("err", "Offline", "Unable to reach the server");
      els.healthBanner.hidden = false;
      els.healthBanner.className = "banner err";
      els.healthBanner.textContent =
        "Unable to connect to the server. Start the application and refresh this page.";
    }
  }

  function applyResult(body) {
    lastMarkdown = body.markdown || "";
    lastSourceName =
      body.source_name || (selectedFile && selectedFile.name) || "document.pdf";

    const empty = !lastMarkdown || !String(lastMarkdown).trim();
    setOutput(
      empty ? "No extractable text was found in this PDF." : lastMarkdown,
      { empty }
    );

    if (!empty) {
      setMeta(body.page_count);
      setResultState("ready");
    } else {
      setMeta(null);
      setResultState("empty");
    }

    const warns = body.warnings || [];
    setWarnings(warns, {
      showScanHelp:
        empty || warns.some((w) => /ocr|tesseract|poppler|scan/i.test(String(w))),
    });

    els.btnDownload.disabled = empty;
    els.btnCopy.disabled = empty;
    setResultActionsIdle(empty);
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
        const detail =
          typeof body.detail === "string" ? body.detail : "Conversion failed.";
        throw new Error(detail);
      }

      setProgress(body.progress || 0, body.message || "Processing…");

      if (body.status === "completed") {
        applyResult(body);
        setProgress(100, "Complete");
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
    setOutput("", { empty: true });
    setMeta(null);
    lastMarkdown = "";
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
        const detail =
          typeof body.detail === "string"
            ? body.detail
            : "Unable to start conversion.";
        throw new Error(detail);
      }
      setProgress(8, "Queued…");
      await pollJob(body.job_id);
    } catch (err) {
      setOutput("", { empty: true });
      setError(String(err.message || err));
      lastMarkdown = "";
      els.btnDownload.disabled = true;
      els.btnCopy.disabled = true;
      setResultActionsIdle(true);
      setResultState("empty");
      setMeta(null);
      els.progressWrap.hidden = true;
    } finally {
      setBusy(false);
      if (lastMarkdown) {
        els.progressWrap.hidden = true;
      }
    }
  }

  function downloadMd() {
    if (!lastMarkdown) return;
    const stem = (lastSourceName || "document").replace(/\.pdf$/i, "");
    const blob = new Blob([lastMarkdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${stem}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function copyMd() {
    if (!lastMarkdown) return;
    try {
      await navigator.clipboard.writeText(lastMarkdown);
      const prev = els.btnCopy.textContent;
      els.btnCopy.textContent = "Copied";
      setTimeout(() => {
        els.btnCopy.textContent = prev;
      }, 1400);
    } catch {
      setError("Unable to copy to the clipboard. Use Download instead.");
    }
  }

  els.dropzone.addEventListener("click", (e) => {
    if (e.target.closest("#btn-clear")) return;
    if (selectedFile && e.target.closest(".dropzone-file, .uploader-file")) return;
    els.fileInput.click();
  });

  els.dropzone.addEventListener("keydown", (e) => {
    if ((e.key === "Enter" || e.key === " ") && !selectedFile) {
      e.preventDefault();
      els.fileInput.click();
    }
  });

  els.fileInput.addEventListener("change", () => {
    if (els.fileInput.files && els.fileInput.files[0]) {
      setFile(els.fileInput.files[0]);
    }
  });

  if (els.btnClear) els.btnClear.addEventListener("click", clearFile);

  ["dragenter", "dragover"].forEach((ev) => {
    els.dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (!selectedFile) els.dropzone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach((ev) => {
    els.dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      els.dropzone.classList.remove("dragover");
    });
  });
  els.dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) setFile(file);
  });

  els.btnConvert.addEventListener("click", convert);
  els.btnDownload.addEventListener("click", downloadMd);
  els.btnCopy.addEventListener("click", copyMd);

  setPreviewEmpty(true);
  setResultState("empty");
  setResultActionsIdle(true);
  refreshHealth();
})();
