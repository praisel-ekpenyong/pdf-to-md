/**
 * PDF → Markdown — theme toggle
 * Applies light/dark theme, persists choice in localStorage, and keeps the
 * <meta name="theme-color"> in sync so the browser chrome matches the page.
 *
 * The initial data-theme attribute is set by an inline script in <head> so the
 * first paint is already correct. This module only wires up the toggle button
 * and reacts to system changes when the user has not made an explicit choice.
 */
(() => {
  "use strict";

  const STORAGE_KEY = "pdfmd:theme";
  const THEME_LIGHT = "light";
  const THEME_DARK = "dark";

  const root = document.documentElement;

  function currentExplicit() {
    const v = root.getAttribute("data-theme");
    return v === THEME_LIGHT || v === THEME_DARK ? v : null;
  }

  function stored() {
    try {
      const v = localStorage.getItem(STORAGE_KEY);
      return v === THEME_LIGHT || v === THEME_DARK ? v : null;
    } catch {
      return null;
    }
  }

  function systemPrefersLight() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: light)").matches
    );
  }

  function effectiveTheme() {
    return (
      stored() ||
      currentExplicit() ||
      (systemPrefersLight() ? THEME_LIGHT : THEME_DARK)
    );
  }

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    syncThemeColorMeta(theme);
    reflectToggleState(theme);
  }

  function syncThemeColorMeta(theme) {
    const light = "#f6f4ef";
    const dark = "#0f1011";
    const color = theme === THEME_LIGHT ? light : dark;
    const metas = document.querySelectorAll('meta[name="theme-color"]');
    metas.forEach((m) => {
      if (!m.hasAttribute("media")) m.setAttribute("content", color);
    });
  }

  function reflectToggleState(theme) {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    const isLight = theme === THEME_LIGHT;
    btn.setAttribute("aria-pressed", String(isLight));
    btn.setAttribute(
      "aria-label",
      isLight ? "Switch to dark theme" : "Switch to light theme"
    );
    btn.title = isLight ? "Switch to dark" : "Switch to light";
  }

  function toggle() {
    const next = effectiveTheme() === THEME_LIGHT ? THEME_DARK : THEME_LIGHT;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* localStorage blocked — still apply for this session */
    }
    applyTheme(next);
  }

  function init() {
    // Reconcile state on load: if no explicit attribute was set by the head
    // script (e.g. localStorage was blocked), fall back to system preference.
    if (!currentExplicit()) {
      const storedTheme = stored();
      applyTheme(
        storedTheme || (systemPrefersLight() ? THEME_LIGHT : THEME_DARK)
      );
    } else {
      // Attribute already set — sync the meta + button state to match.
      applyTheme(currentExplicit());
    }

    const btn = document.getElementById("theme-toggle");
    if (btn) btn.addEventListener("click", toggle);

    // If the user has not chosen, follow system changes live.
    const mq = window.matchMedia
      ? window.matchMedia("(prefers-color-scheme: light)")
      : null;
    if (mq && typeof mq.addEventListener === "function") {
      mq.addEventListener("change", (e) => {
        if (stored()) return;
        applyTheme(e.matches ? THEME_LIGHT : THEME_DARK);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
