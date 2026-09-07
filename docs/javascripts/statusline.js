/*
 * statusline.js — fixed bottom "editor statusline" bar for every page.
 *
 * Built against the real Zensical 0.0.59 output (site/index.html and
 * site/modules/authentication/jwt/index.html):
 *
 *   <!-- generated:page-footer start -->
 *   <p><strong>Status:</strong> reviewed · <strong>Last reviewed:</strong> ...</p>
 *   <!-- generated:page-footer end -->
 *
 *   <h2 id="references">References</h2>
 *   <!-- generated:references start -->
 *   <table>...<tbody><tr>...</tr>...</tbody></table>   (or)
 *   <p><em>No sources recorded yet.</em></p>
 *   <!-- generated:references end -->
 *
 * Comments are not elements, so they cannot be selected directly; we key
 * off the surrounding real elements instead (see selectors below).
 */
(function () {
  'use strict';

  // ---- status: find the <strong>Status:</strong> label, then read the
  // rest of its parent <p> (page-footer has no id/class hook, but the
  // literal "Status:" label is stable and unique on every page).
  function readStatus() {
    var strongs = document.querySelectorAll('strong');
    for (var i = 0; i < strongs.length; i++) {
      if (strongs[i].textContent.trim() === 'Status:') {
        var text = strongs[i].parentElement ? strongs[i].parentElement.textContent : '';
        var m = /reviewed|draft|stub/i.exec(text);
        return m ? m[0].toLowerCase() : null;
      }
    }
    return null;
  }

  // ---- sources: the References section always has an <h2 id="references">;
  // the generated block is its next real element (a <table> of sources, or
  // a <p><em>No sources recorded yet.</em></p> fallback).
  function countSources() {
    var heading = document.getElementById('references');
    if (!heading) return 0;
    var next = heading.nextElementSibling;
    if (!next) return 0;
    if (next.tagName === 'TABLE') {
      return next.querySelectorAll('tbody tr').length;
    }
    if (next.tagName === 'UL' || next.tagName === 'OL') {
      return next.querySelectorAll('li').length;
    }
    return 0;
  }

  // ---- path: Zensical embeds <script id="__config" type="application/json">
  // with a "base" field — a relative path from the current page back to the
  // site root (e.g. "../../.."). Resolving it against location.href gives
  // the real site-root path in any deployment (root or GitHub Pages
  // sub-path) without hardcoding a domain or base prefix.
  function readPagePath() {
    var root = null;
    try {
      var cfgEl = document.getElementById('__config');
      if (cfgEl) {
        var cfg = JSON.parse(cfgEl.textContent);
        if (typeof cfg.base === 'string') {
          root = new URL(cfg.base, location.href).pathname;
        }
      }
    } catch (e) { /* fall through to raw pathname */ }

    var pathname = location.pathname;
    var rel = pathname;
    if (root && pathname.indexOf(root) === 0) {
      rel = pathname.slice(root.length);
    } else {
      rel = pathname.replace(/^\//, '');
    }
    rel = rel.replace(/index\.html$/, '').replace(/\/$/, '');
    return rel === '' ? '~' : rel;
  }

  function makeSeg(tag, className, text) {
    var el = document.createElement(tag);
    if (className) el.className = className;
    el.textContent = text;
    return el;
  }

  function renderBar() {
    var existing = document.querySelector('.ti-statusline');
    if (existing) existing.remove();

    var footer = document.createElement('footer');
    footer.className = 'ti-statusline';
    footer.setAttribute('role', 'contentinfo');
    footer.setAttribute('aria-label', 'Page status');

    try {
      var status = readStatus();
      var path = readPagePath();
      var sources = countSources();

      footer.appendChild(makeSeg('span', 'ti-mode', status ? status.toUpperCase() : 'PLAYBOOK'));
      footer.appendChild(makeSeg('span', 'ti-seg ti-path', path));

      if (status) {
        var glyph = status === 'reviewed' ? '✓' : status === 'draft' ? '●' : '○';
        var statusSpan = makeSeg('span', 'ti-seg ti-status', glyph + ' ' + status);
        statusSpan.setAttribute('data-status', status);
        footer.appendChild(statusSpan);
      }

      if (sources > 0) {
        footer.appendChild(makeSeg('span', 'ti-seg ti-sources', sources + ' sources'));
      }

      footer.appendChild(makeSeg('span', 'ti-seg ti-right', 'Engineering Playbook'));
    } catch (e) {
      // Parsing failed for some reason — never break the page, fall back
      // to a minimal bar with just mode + path.
      footer.textContent = '';
      footer.appendChild(makeSeg('span', 'ti-mode', 'PLAYBOOK'));
      var fallbackPath = '~';
      try { fallbackPath = readPagePath(); } catch (e2) { /* give up */ }
      footer.appendChild(makeSeg('span', 'ti-seg ti-path', fallbackPath));
    }

    document.body.appendChild(footer);
  }

  function safeRender() {
    try { renderBar(); } catch (e) { /* never break the page */ }
  }

  // ---- instant navigation hook: Material's bundle exposes
  // window.document$, an RxJS-like Observable that emits on the initial
  // load and again on every SPA-style page swap (navigation.instant).
  // Confirmed present in site/assets/javascripts/bundle.*.min.js via
  // "window.document$=yt;". Subscribing there covers every render.
  if (window.document$ && typeof window.document$.subscribe === 'function') {
    window.document$.subscribe(safeRender);
  } else {
    // Fallback: run once on load, then watch for instant-nav DOM swaps by
    // observing the document body (debounced to coalesce bursts of
    // mutations from a single page swap).
    document.addEventListener('DOMContentLoaded', safeRender);

    if (window.MutationObserver) {
      var debounceTimer = null;
      var observer = new MutationObserver(function () {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(safeRender, 50);
      });
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }
})();
