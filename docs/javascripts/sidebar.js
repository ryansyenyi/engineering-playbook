/*
 * sidebar.js — restyles + enhances the generated Zensical left sidebar to
 * match mockups/sidebar-shadcn.html (shadcn-anatomy x Terminal Ink):
 * brand header + search button, status dots, section count badges,
 * top-level icons, footer repo card + coverage bar, desktop offcanvas
 * collapse (Ctrl+B). Vanilla, no deps, try/catch guarded throughout so a
 * failure here never breaks the underlying Zensical nav.
 *
 * Built against the real Zensical 0.0.59 output (site/index.html and
 * site/modules/authentication/jwt/index.html):
 *
 *   .md-sidebar--primary > .md-sidebar__scrollwrap > .md-sidebar__inner
 *     > nav.md-nav--primary > ul.md-nav__list > li.md-nav__item ...
 *
 * Leaf item:    <li class="md-nav__item"><a class="md-nav__link" href="…">…</a></li>
 * Section item: <li class="md-nav__item md-nav__item--section md-nav__item--nested">
 *                 <input class="md-nav__toggle" type="checkbox" id="__nav_N">
 *                 <div class="md-nav__link md-nav__container">
 *                   <a class="md-nav__link" href="…">…</a>          <!-- navigation.indexes -->
 *                   <label class="md-nav__link" for="__nav_N">…</label>  <!-- toggle chevron -->
 *                 </div>
 *                 <nav class="md-nav" data-md-level="…">…</nav>
 *               </li>
 * Section without an index page (e.g. "What's moving") has no inner <a>,
 * only the toggle <label class="md-nav__link" for="__nav_N">.
 *
 * Search: real toggle is a hidden checkbox
 *   <input class="md-toggle" data-md-toggle="search" type="checkbox" id="__search">
 * opened normally by <label for="__search"> in the header. Programmatic
 * open = check it + dispatch a "change" event (mirrors the label click),
 * then focus .md-search__input. Confirmed present in site/index.html.
 *
 * __config base-path trick reused verbatim from statusline.js to resolve
 * any nav href to a docs-path key ("modules/authentication/jwt", "index").
 *
 * Desktop offcanvas: main.5da3a30f.min.css shows
 *   .md-main__inner { display:flex }
 *   .md-content { flex-grow:1; min-width:0 }
 *   .md-sidebar (desktop) { position:sticky; width:12.1rem }
 * so simply display:none-ing .md-sidebar--primary lets .md-content reflow
 * to fill the freed width — no grid-template surgery needed. Guarded to
 * the >=76.25em breakpoint (Zensical's own mobile-drawer cutoff) so the
 * native mobile drawer (#__drawer checkbox) is never touched.
 */
(function () {
  'use strict';

  var LS_KEY = 'ti.sidebar.collapsed';

  // ---- 0. Restore collapsed state as early as possible (before first
  // paint where the script's position in the document allows it). ----
  try {
    if (localStorage.getItem(LS_KEY) === '1' && document.body) {
      document.body.classList.add('ti-sb-collapsed');
    }
  } catch (e) { /* localStorage unavailable — never break the page */ }

  // ---- lucide-style 16px icon paths (stroke=currentColor, stroke-width=2) ----
  var ICONS = {
    'playbook':
      '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/>' +
      '<path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    'principles':
      '<path d="M6 3h12l4 6-10 13L2 9Z"/><path d="M11 3 8 9l4 13 4-13-3-6"/><path d="M2 9h20"/>',
    'modules':
      '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/>' +
      '<rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    'security':
      '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    'decisions':
      '<line x1="6" x2="6" y1="3" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>',
    'checklists':
      '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="m9 12 2 2 4-4"/>',
    'matrices':
      '<path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/>',
    'tags':
      '<line x1="4" x2="20" y1="9" y2="9"/><line x1="4" x2="20" y1="15" y2="15"/>' +
      '<line x1="10" x2="8" y1="3" y2="21"/><line x1="16" x2="14" y1="3" y2="21"/>',
    "what's moving":
      '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>'
  };

  var STATUS_TITLE = {
    reviewed: 'Status: reviewed',
    draft: 'Status: draft',
    stub: 'Status: stub — not yet written'
  };

  function svgIcon(inner) {
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" ' +
      'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ' +
      'width="16" height="16" aria-hidden="true" focusable="false">' + inner + '</svg>';
  }

  // ---- __config base-path trick (verbatim pattern from statusline.js) ----
  function readConfigRoot() {
    try {
      var cfgEl = document.getElementById('__config');
      if (cfgEl) {
        var cfg = JSON.parse(cfgEl.textContent);
        if (typeof cfg.base === 'string') {
          return new URL(cfg.base, location.href).pathname;
        }
      }
    } catch (e) { /* fall through */ }
    return null;
  }

  function resolveDocsPath(href, root) {
    try {
      if (!href && href !== '') return null;
      var abs = new URL(href, location.href).pathname;
      var rel;
      if (root && abs.indexOf(root) === 0) {
        rel = abs.slice(root.length);
      } else {
        rel = abs.replace(/^\//, '');
      }
      rel = rel.replace(/index\.html$/, '').replace(/\/$/, '');
      return rel === '' ? 'index' : rel;
    } catch (e) {
      return null;
    }
  }

  // Every built href is a "pretty URL" directory (trailing slash, no
  // filename) whether the source was <name>.md (leaf page, key = "<name>")
  // or <name>/index.md (section index, key = "<name>/index") — the two are
  // indistinguishable from the URL alone, so look up both candidate keys
  // against the pages map (confirmed against the real generated
  // nav-data.js: "modules/authentication/email-password" has no /index
  // suffix, but "modules/authentication/index" does).
  function lookupPage(pages, key) {
    if (!key) return undefined;
    if (Object.prototype.hasOwnProperty.call(pages, key)) return pages[key];
    var withIndex = key + '/index';
    if (Object.prototype.hasOwnProperty.call(pages, withIndex)) return pages[withIndex];
    return undefined;
  }

  function labelTextOf(el) {
    if (!el) return '';
    var ellipsis = el.querySelector('.md-ellipsis');
    var text = ellipsis ? ellipsis.textContent : el.textContent;
    return (text || '').replace(/\s+/g, ' ').trim();
  }

  // ---- search relocation ----
  // The modern search dialog only opens on a *trusted* click routed through
  // the bundle's listener on the .md-search container; synthetic .click()
  // and checkbox toggling are ignored. So instead of a proxy button we
  // physically move the whole .md-search element (listeners travel with the
  // node) into the sidebar slot on desktop, and put it back in the header
  // below Zensical's drawer breakpoint so mobile search stays in the header.
  var searchHome = null; // { parent, next } — original header position

  function placeSearch() {
    try {
      var search = document.querySelector('.md-search');
      if (!search) return;
      if (!searchHome) {
        searchHome = { parent: search.parentNode, next: search.nextSibling };
      }
      var slot = document.querySelector('.ti-sb-search-slot');
      if (isDesktop() && slot) {
        if (search.parentNode !== slot) slot.appendChild(search);
      } else if (searchHome.parent && search.parentNode !== searchHome.parent) {
        searchHome.parent.insertBefore(search, searchHome.next);
      }
    } catch (e) { /* never break the page */ }
  }

  function isDesktop() {
    try {
      return matchMedia('(min-width: 76.25em)').matches;
    } catch (e) {
      return true;
    }
  }

  function toggleCollapsed() {
    try {
      var collapsed = document.body.classList.toggle('ti-sb-collapsed');
      localStorage.setItem(LS_KEY, collapsed ? '1' : '0');
    } catch (e) { /* ignore */ }
  }

  // ---- header brand card + search button ----
  function injectHeaderCard(status) {
    try {
      var inner = document.querySelector('.md-sidebar--primary .md-sidebar__inner');
      if (!inner) return;
      if (inner.querySelector('.ti-sb-header')) return; // idempotent

      var totals = status && status.totals;

      var header = document.createElement('div');
      header.className = 'ti-sb-header';

      var brand = document.createElement('div');
      brand.className = 'ti-sb-brand';

      var mark = document.createElement('span');
      mark.className = 'ti-sb-mark';
      mark.textContent = 'EP';

      var t = document.createElement('span');
      t.className = 'ti-sb-brand-t';
      var b = document.createElement('b');
      b.textContent = 'Engineering Playbook';
      var small = document.createElement('small');
      small.textContent = 'main · ' + (totals && typeof totals.total === 'number' ? totals.total : '?') + ' pages';
      t.appendChild(b);
      t.appendChild(small);

      brand.appendChild(mark);
      brand.appendChild(t);

      // slot the real .md-search element is moved into (see placeSearch)
      var searchSlot = document.createElement('div');
      searchSlot.className = 'ti-sb-search-slot';

      header.appendChild(brand);
      header.appendChild(searchSlot);

      inner.insertBefore(header, inner.firstChild);
    } catch (e) { /* never break the page */ }
  }

  // ---- footer: repo card + coverage bar + legend ----
  function injectFooterCard(status) {
    try {
      var inner = document.querySelector('.md-sidebar--primary .md-sidebar__inner');
      if (!inner) return;
      if (inner.querySelector('.ti-sb-footer')) return; // idempotent

      var totals = (status && status.totals) || null;

      var repoUrl = 'https://github.com/ryansyenyi/engineering-playbook';
      try {
        var srcLink = document.querySelector(
          '.md-sidebar--primary .md-nav__source .md-source, .md-header__source .md-source'
        );
        if (srcLink && srcLink.getAttribute('href')) {
          repoUrl = srcLink.getAttribute('href');
        }
      } catch (e2) { /* keep fallback */ }

      var footer = document.createElement('div');
      footer.className = 'ti-sb-footer';

      var user = document.createElement('a');
      user.className = 'ti-sb-user';
      user.href = repoUrl;
      user.target = '_blank';
      user.rel = 'noopener';
      user.title = 'Repository';

      var av = document.createElement('span');
      av.className = 'ti-sb-av';
      av.textContent = 'ry';

      var ut = document.createElement('span');
      ut.className = 'ti-sb-user-t';
      var ub = document.createElement('b');
      ub.textContent = 'ryansyenyi/engineering-playbook';
      var us = document.createElement('small');
      us.textContent = 'GitHub · main';
      ut.appendChild(ub);
      ut.appendChild(us);

      user.appendChild(av);
      user.appendChild(ut);
      footer.appendChild(user);

      if (totals && typeof totals.total === 'number' && totals.total > 0) {
        var reviewed = totals.reviewed || 0;
        var draft = totals.draft || 0;
        var stub = totals.stub || 0;
        var total = totals.total;
        var pct = function (n) { return (n / total) * 100; };

        var cov = document.createElement('div');
        cov.className = 'ti-sb-coverage';
        cov.setAttribute('role', 'img');
        cov.setAttribute(
          'aria-label',
          'Coverage: ' + reviewed + ' reviewed, ' + draft + ' draft, ' + stub + ' stub'
        );
        cov.title =
          'Playbook coverage: ' + reviewed + ' reviewed, ' + draft + ' draft, ' +
          stub + ' stub (' + total + ' pages)';

        [['reviewed', reviewed], ['draft', draft], ['stub', stub]].forEach(function (pair) {
          var seg = document.createElement('i');
          seg.className = 'ti-cov-' + pair[0];
          seg.style.width = pct(pair[1]) + '%';
          cov.appendChild(seg);
        });
        footer.appendChild(cov);

        var legend = document.createElement('div');
        legend.className = 'ti-sb-legend';
        [
          ['reviewed', 'Pages fully reviewed against sources'],
          ['draft', 'Pages drafted, not yet reviewed'],
          ['stub', 'Placeholder pages, no content yet']
        ].forEach(function (pair) {
          var span = document.createElement('span');
          span.title = pair[1];
          var dot = document.createElement('span');
          dot.className = 'ti-dot';
          dot.setAttribute('data-status', pair[0]);
          span.appendChild(dot);
          span.appendChild(document.createTextNode(' ' + (totals[pair[0]] || 0) + ' ' + pair[0]));
          legend.appendChild(span);
        });
        footer.appendChild(legend);
      }

      inner.appendChild(footer);
    } catch (e) { /* never break the page */ }
  }

  // ---- nav decoration: icons on top-level items, status dots on every
  // resolvable link, count badges on every resolvable section. ----
  function decorateTopIcon(li) {
    try {
      var link = li.querySelector(':scope > a.md-nav__link, :scope > .md-nav__container > a.md-nav__link');
      var label = li.querySelector(':scope > label.md-nav__link, :scope > .md-nav__container > label.md-nav__link');
      var target = link || label;
      if (!target) return;
      var text = labelTextOf(target).toLowerCase();
      var iconInner = ICONS[text];
      if (!iconInner) return; // not in the fixed name->icon map — skip silently
      if (target.querySelector('.ti-ico')) return;
      var span = document.createElement('span');
      span.className = 'ti-ico';
      span.innerHTML = svgIcon(iconInner);
      var ellipsis = target.querySelector('.md-ellipsis');
      if (ellipsis) target.insertBefore(span, ellipsis);
      else target.insertBefore(span, target.firstChild);
    } catch (e) { /* skip this item */ }
  }

  function addDot(a, statusVal) {
    try {
      if (!statusVal || !STATUS_TITLE[statusVal]) return;
      if (a.querySelector('.ti-dot')) return;
      var dot = document.createElement('span');
      dot.className = 'ti-dot';
      dot.setAttribute('data-status', statusVal);
      dot.title = STATUS_TITLE[statusVal];
      a.appendChild(dot);
    } catch (e) { /* skip */ }
  }

  function addBadge(el, counts) {
    try {
      if (!counts || typeof counts.total !== 'number') return;
      if (el.querySelector('.ti-badge')) return;
      var badge = document.createElement('span');
      badge.className = 'ti-badge';
      badge.textContent = String(counts.total);
      badge.title = counts.total + ' pages in this section';
      el.appendChild(badge);
    } catch (e) { /* skip */ }
  }

  function decorateNav(status) {
    try {
      var nav = document.querySelector('.md-sidebar--primary .md-nav--primary');
      if (!nav) return;
      var topList = nav.querySelector(':scope > ul.md-nav__list');
      if (!topList) return;
      if (topList.hasAttribute('data-ti-decorated')) return; // idempotent
      topList.setAttribute('data-ti-decorated', '1');

      var root = readConfigRoot();
      var pages = (status && status.pages) || {};
      var sections = (status && status.sections) || {};

      var topItems = topList.querySelectorAll(':scope > li.md-nav__item');
      topItems.forEach(decorateTopIcon);

      // Badges before dots: a section index link can be BOTH a section
      // (badge) and a resolvable page (dot) — run badges first so the
      // final DOM order is label, badge, dot (matches the
      // ".ti-badge + .ti-dot" spacing rule in extra.css).
      // "On this page" (.md-nav--secondary) is nested inside the active
      // top-level <li>, not a sibling — exclude its links/anchors from
      // primary-nav decoration.
      var sectionItems = nav.querySelectorAll('li.md-nav__item--section');
      sectionItems.forEach(function (li) {
        try {
          if (li.closest('.md-nav--secondary')) return;
          var link = li.querySelector(':scope > .md-nav__container > a.md-nav__link, :scope > a.md-nav__link');
          var toggleLabel = li.querySelector(':scope > .md-nav__container > label.md-nav__link, :scope > label.md-nav__link');
          var target = link || toggleLabel;
          if (!link || !target) return; // no resolvable index href — skip silently
          var key = resolveDocsPath(link.getAttribute('href'), root);
          if (key && Object.prototype.hasOwnProperty.call(sections, key)) {
            addBadge(target, sections[key]);
          }
        } catch (e) { /* skip this section */ }
      });

      var allLinks = nav.querySelectorAll('a.md-nav__link[href]');
      allLinks.forEach(function (a) {
        try {
          if (a.closest('.md-nav--secondary')) return;
          var key = resolveDocsPath(a.getAttribute('href'), root);
          var pageStatus = lookupPage(pages, key);
          if (pageStatus) addDot(a, pageStatus);
        } catch (e) { /* skip this link */ }
      });
    } catch (e) { /* never break the page */ }
  }

  // ---- desktop collapse toggle in the header, near the site title ----
  function injectCollapseToggle() {
    try {
      if (document.querySelector('.ti-sb-toggle')) return; // idempotent
      var titleWrap = document.querySelector('.md-header__title');
      if (!titleWrap || !titleWrap.parentNode) return;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ti-sb-toggle';
      btn.title = 'Toggle sidebar (Ctrl+B)';
      btn.setAttribute('aria-label', 'Toggle sidebar');
      btn.textContent = '⫸'; // ⫸
      btn.addEventListener('click', function () {
        if (!isDesktop()) return;
        toggleCollapsed();
      });
      titleWrap.parentNode.insertBefore(btn, titleWrap.nextSibling);
    } catch (e) { /* never break the page */ }
  }

  var keydownBound = false;
  function bindKeybinding() {
    if (keydownBound) return;
    keydownBound = true;
    document.addEventListener('keydown', function (e) {
      try {
        if (!(e.ctrlKey || e.metaKey)) return;
        if (!e.key || e.key.toLowerCase() !== 'b') return;
        if (!isDesktop()) return;
        e.preventDefault();
        toggleCollapsed();
      } catch (e2) { /* ignore */ }
    });
  }

  function safeRender() {
    try {
      var status = window.__navStatus || null;
      injectHeaderCard(status);
      injectFooterCard(status);
      decorateNav(status);
      injectCollapseToggle();
      bindKeybinding();
      placeSearch();
    } catch (e) { /* never break the page */ }
  }

  // keep search in the right home when the viewport crosses the breakpoint
  try {
    matchMedia('(min-width: 76.25em)').addEventListener('change', placeSearch);
  } catch (e) { /* older API or unavailable — resize keeps mobile default */ }

  // ---- instant navigation hook (same pattern as statusline.js) ----
  if (window.document$ && typeof window.document$.subscribe === 'function') {
    window.document$.subscribe(safeRender);
  } else {
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
