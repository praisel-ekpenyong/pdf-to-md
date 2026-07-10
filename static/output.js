/**
 * PDF → Markdown — output page
 * Reads ?job=<id> (or sessionStorage fallback), loads GET /jobs/{id},
 * renders Markdown, wires Copy / Download.
 */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const els = {
    sprout: $("sprout"),
    sproutBar: $("sprout-bar"),
    output: $("output-pre"),
    previewEmpty: $("preview-empty"),
    previewEmptyTitle: $("preview-empty-title"),
    previewEmptyText: $("preview-empty-text"),
    previewSkeleton: $("preview-skeleton"),
    meta: $("meta"),
    error: $("error"),
    warnings: $("warnings"),
    panelResult: $("panel-result"),
    resultActions: $("result-actions"),
    resultTitle: $("result-title"),
    btnCopy: $("btn-copy"),
    btnDownload: $("btn-download"),
    facts: $("facts"),
    factPages: $("fact-pages"),
    factOcr: $("fact-ocr"),
    factSource: $("fact-source"),
  };

  let lastMarkdown = "";
  let lastSourceName = "";
  let pollTimer = null;

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "\u0026amp;")
      .replace(/</g, "\u0026lt;")
      .replace(/>/g, "\u0026gt;")
      .replace(/"/g, "\u0026quot;");
  }

  function setSprout(state, width) {
    if (!els.sprout) return;
    els.sprout.dataset.state = state;
    if (typeof width === "number" && els.sproutBar) els.sproutBar.style.width = `${width}%`;
  }

  function setTitle(label) {
    if (els.resultTitle) els.resultTitle.textContent = label;
    document.title = label && label !== "Loading…"
      ? `${label} · PDF → Markdown`
      : "Output · PDF → Markdown";
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

    const SCAN_HELP =
      "Scanned or image-based pages require a one-time OCR setup on this machine. " +
      "Use Docker Compose, or install Tesseract and Poppler. Text-based PDFs convert without these tools.";

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

  function setSkeleton(on) {
    if (!els.previewSkeleton) return;
    els.previewSkeleton.hidden = !on;
    els.previewSkeleton.setAttribute("aria-hidden", on ? "false" : "true");
  }

  function setEmptyMessage(title, text) {
    if (els.previewEmptyTitle && title) els.previewEmptyTitle.textContent = title;
    if (els.previewEmptyText && text) els.previewEmptyText.textContent = text;
  }

  function setPreviewEmpty(isEmpty) {
    if (els.output) els.output.classList.toggle("is-empty", isEmpty);
    if (!els.previewEmpty) return;
    const skeletonOn = els.previewSkeleton && !els.previewSkeleton.hidden;
    // Show empty state only when empty AND not skeleton-loading
    if (isEmpty && !skeletonOn) {
      els.previewEmpty.hidden = false;
      els.previewEmpty.style.display = "";
    } else {
      els.previewEmpty.hidden = true;
      els.previewEmpty.style.display = "none";
    }
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

  function setFacts({ pages, ocrPages, source } = {}) {
    if (!els.facts) return;
    if (pages == null && ocrPages == null && !source) {
      els.facts.hidden = true;
      return;
    }
    els.facts.hidden = false;
    if (pages != null && els.factPages) els.factPages.textContent = String(pages);
    if (ocrPages != null && els.factOcr) {
      const arr = Array.isArray(ocrPages) ? ocrPages : [];
      els.factOcr.textContent = arr.length ? arr.join(", ") : "—";
    }
    if (source && els.factSource) els.factSource.textContent = source;
  }

  function setProgress(pct) {
    const p = Math.max(0, Math.min(100, pct || 0));
    setSprout(p >= 100 ? "done" : "on", p);
  }

  function mdNameFromSource(sourceName) {
    const stem = (sourceName || "document").replace(/\.pdf$/i, "") || "document";
    return `${stem}.md`;
  }

  function applyResult(body) {
    lastMarkdown = body.markdown || "";
    lastSourceName = body.source_name || "document.pdf";
    const fileLabel = mdNameFromSource(lastSourceName);
    setTitle(fileLabel);

    // Nearly empty titles-only markdown still counts as content if non-whitespace remains.
    const empty = !lastMarkdown || !String(lastMarkdown).trim();
    if (els.output) els.output.textContent = empty ? "" : lastMarkdown;

    setSkeleton(false);
    setError("");

    if (empty) {
      setEmptyMessage(
        "No extractable text",
        "This PDF produced no usable text. It may be a scan that needs OCR setup."
      );
      setPreviewEmpty(true);
      setMeta(null);
      setResultState("empty");
      setFacts({
        pages: body.page_count,
        ocrPages: body.ocr_pages,
        source: lastSourceName,
      });
      setSprout("off", 0);
    } else {
      setPreviewEmpty(false);
      setMeta(body.page_count);
      setResultState("ready");
      setFacts({
        pages: body.page_count,
        ocrPages: body.ocr_pages,
        source: lastSourceName,
      });
      setProgress(100);
      window.setTimeout(() => setSprout("off", 0), 500);
    }

    const warns = body.warnings || [];
    setWarnings(warns, {
      showScanHelp: empty || warns.some((w) => /ocr|tesseract|poppler|scan/i.test(String(w))),
    });

    if (els.btnDownload) els.btnDownload.disabled = empty;
    if (els.btnCopy) els.btnCopy.disabled = empty;
    setResultActionsIdle(empty);
  }

  function markFailed(message) {
    const msg = message || "Conversion failed.";
    setError(msg);
    setSkeleton(false);
    setEmptyMessage("No output available", msg);
    setPreviewEmpty(true);
    setResultState("empty");
    setResultActionsIdle(true);
    setTitle("output.md");
    setMeta(null);
    setFacts({});
    setSprout("off", 0);
    if (els.btnDownload) els.btnDownload.disabled = true;
    if (els.btnCopy) els.btnCopy.disabled = true;
    if (els.output) {
      els.output.textContent = "";
      els.output.classList.add("is-empty");
    }
  }

  function markLoading() {
    setError("");
    setTitle("Loading…");
    setResultState("busy");
    setSkeleton(true);
    setPreviewEmpty(false);
    setResultActionsIdle(true);
    setProgress(8);
    if (els.btnDownload) els.btnDownload.disabled = true;
    if (els.btnCopy) els.btnCopy.disabled = true;
  }

  function sleep(ms) {
    return new Promise((r) => {
      pollTimer = setTimeout(r, ms);
    });
  }

  async function loadJob(id) {
    markLoading();
    let delay = 400;
    const maxMs = 30 * 60 * 1000;
    const start = Date.now();

    while (Date.now() - start < maxMs) {
      let res;
      let body;
      try {
        res = await fetch(`/jobs/${encodeURIComponent(id)}`);
        body = await res.json();
      } catch {
        markFailed("Unable to reach the server. Start the application and try again.");
        return;
      }

      if (!res.ok) {
        const detail =
          body && typeof body.detail === "string"
            ? body.detail
            : res.status === 404
              ? "Job not found. It may have expired after a server restart. Convert the file again."
              : "Could not load conversion result.";
        markFailed(detail);
        return;
      }

      if (body.status === "completed") {
        applyResult(body);
        return;
      }
      if (body.status === "failed") {
        markFailed(body.error || "Conversion failed.");
        return;
      }

      // Still running / queued
      setProgress(body.progress || 0);
      setResultState("busy");
      setSkeleton(true);
      setPreviewEmpty(false);
      if (body.message) {
        setEmptyMessage("Converting", body.message);
      }

      await sleep(delay);
      delay = Math.min(delay * 1.25, 2000);
    }
    markFailed("Conversion is taking too long. Return home and try again.");
  }

  function downloadMd() {
    if (!lastMarkdown) return;
    const name = mdNameFromSource(lastSourceName);
    const blob = new Blob([lastMarkdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function copyMd() {
    if (!lastMarkdown) return;
    try {
      await navigator.clipboard.writeText(lastMarkdown);
      const label = els.btnCopy && els.btnCopy.querySelector("span");
      if (label) {
        const prev = label.textContent;
        label.textContent = "Copied";
        setTimeout(() => {
          label.textContent = prev;
        }, 1400);
      }
    } catch {
      setError("Unable to copy to the clipboard. Use Download instead.");
    }
  }

  function resolveJobId() {
    const params = new URLSearchParams(window.location.search);
    const fromUrl = params.get("job");
    if (fromUrl && fromUrl.trim()) return fromUrl.trim();
    try {
      const fromStorage = sessionStorage.getItem("pdfmd:job_id");
      if (fromStorage && fromStorage.trim()) return fromStorage.trim();
    } catch {
      // sessionStorage unavailable
    }
    return null;
  }

  if (els.btnCopy) els.btnCopy.addEventListener("click", copyMd);
  if (els.btnDownload) els.btnDownload.addEventListener("click", downloadMd);

  const jobId = resolveJobId();
  if (!jobId) {
    markFailed("No conversion found. Return to the home page to convert a PDF.");
  } else {
    loadJob(jobId);
  }
})();
