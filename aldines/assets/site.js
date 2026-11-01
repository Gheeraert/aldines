/* Aucun service distant, aucun suivi, aucune dépendance JavaScript. */
(() => {
  'use strict';
  const one = s => document.querySelector(s);
  const body = document.body;
  const header = one('.reading-header');
  if (header) {
    const measureHeader = () => document.documentElement.style.setProperty('--header-height', `${Math.ceil(header.getBoundingClientRect().height)}px`);
    measureHeader();
    new ResizeObserver(measureHeader).observe(header);
  }
  const storage = {
    get(key) { try { return localStorage.getItem('aldines-' + key); } catch { return null; } },
    set(key, value) { try { localStorage.setItem('aldines-' + key, value); } catch {} }
  };
  const theme = storage.get('theme');
  if (theme === 'light' || theme === 'dark') document.documentElement.dataset.theme = theme;
  one('#theme-toggle')?.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    storage.set('theme', next);
  });
  function changeMode(mode) {
    const rows = [...document.querySelectorAll('.aligned-row.sentence')];
    const toolbarBottom = one('.site-header')?.getBoundingClientRect().bottom || 0;
    const visible = rows.find(r => r.getBoundingClientRect().bottom > toolbarBottom);
    const offset = visible?.getBoundingClientRect().top;
    body.dataset.mode = mode;
    if (visible) window.scrollBy(0, visible.getBoundingClientRect().top - offset);
  }
  const mode = storage.get('reading-mode');
  if (['bilingual', 'latin', 'french'].includes(mode)) {
    body.dataset.mode = mode;
    one('#reading-mode').value = mode;
  }
  one('#reading-mode')?.addEventListener('change', e => {
    changeMode(e.target.value);
    storage.set('reading-mode', e.target.value);
  });
  one('#reader-options')?.addEventListener('click', e => {
    const panel = one('#display-options');
    panel.hidden = !panel.hidden;
    e.target.setAttribute('aria-expanded', String(!panel.hidden));
  });
  document.querySelectorAll('[data-option]').forEach(input => {
    const saved = storage.get('show-' + input.dataset.option);
    if (saved === 'true' || saved === 'false') input.checked = saved === 'true';
    body.classList.toggle('hide-' + input.dataset.option, !input.checked);
    input.addEventListener('change', () => {
      body.classList.toggle('hide-' + input.dataset.option, !input.checked);
      storage.set('show-' + input.dataset.option, String(input.checked));
    });
  });
  document.querySelectorAll('.note-call').forEach((button, index) => {
    const note = button.nextElementSibling;
    note.classList.add(button.closest('.marginalia') ? 'marginalia-content' : 'editorial-note');
    note.id ||= `aldines-note-${index}`;
    button.setAttribute('aria-controls', note.id);
    // Une note ouverte se place après la phrase pour ne pas couper un mot ou
    // interrompre la syntaxe à son point d’ancrage.
    button.closest('.latin, .french')?.append(note);
    button.addEventListener('click', () => {
      note.hidden = !note.hidden;
      button.setAttribute('aria-expanded', String(!note.hidden));
    });
  });
  function revealHash() {
    const id = decodeURIComponent(location.hash.slice(1));
    const target = document.getElementById(id);
    if (!target) return;
    if (target.closest('.latin') && body.dataset.mode === 'french') {
      changeMode('bilingual');
      if (one('#reading-mode')) one('#reading-mode').value = 'bilingual';
    }
    if (target.closest('.french') && body.dataset.mode === 'latin') {
      changeMode('bilingual');
      if (one('#reading-mode')) one('#reading-mode').value = 'bilingual';
    }
    const content = target.closest('.note-content');
    if (content) {
      content.hidden = false;
      document.querySelector(`[aria-controls="${CSS.escape(content.id)}"]`)?.setAttribute('aria-expanded', 'true');
    }
    (target.closest('.aligned-row') || target).scrollIntoView();
  }
  if (location.hash) revealHash();
  window.addEventListener('hashchange', revealHash);
  const navigator = one('#corpus-navigator');
  if (navigator) {
    const entries = [...document.querySelectorAll('.contents-list li')].map(li => ({
      tome: li.dataset.tome, book: li.dataset.book,
      sentences: Number(li.dataset.sentences), translated: Number(li.dataset.translated),
      label: li.querySelector('a').textContent, href: li.querySelector('a').getAttribute('href')
    }));
    const tome = one('#nav-tome'), book = one('#nav-book'), unit = one('#nav-unit');
    function fill(select, options, preferred) {
      select.replaceChildren(...options.map(([value, label]) => new Option(label, value)));
      if (options.some(([value]) => value === preferred)) select.value = preferred;
    }
    function updateUnit() {
      const inBook = entries.filter(e => e.tome === tome.value && e.book === book.value);
      const selected = inBook.find(e => e.href === unit.value);
      if (!selected) return;
      const total = key => inBook.reduce((sum, e) => sum + e[key], 0);
      one('#nav-summary').textContent = `Livre ${book.value} : ${total('sentences')} phrases, ${total('translated')} traduites. Sélection : ${selected.sentences} phrases, ${selected.translated} traduites.`;
      one('#nav-open').href = selected.href;
      storage.set('navigation', JSON.stringify({tome: tome.value, book: book.value, unit: unit.value}));
    }
    function updateBook(preferredUnit) {
      fill(unit, entries.filter(e => e.tome === tome.value && e.book === book.value)
        .map(e => [e.href, `${e.label} — ${e.sentences} phrases · ${e.translated} traduites`]), preferredUnit);
      updateUnit();
    }
    function updateTome(preferredBook, preferredUnit) {
      const inTome = entries.filter(e => e.tome === tome.value);
      fill(book, [...new Set(inTome.map(e => e.book))].map(b => [b, `Livre ${b} — ${inTome.filter(e => e.book === b).length} unités`]), preferredBook);
      updateBook(preferredUnit);
    }
    let previous = {};
    try { previous = JSON.parse(storage.get('navigation')) || {}; } catch {}
    fill(tome, [...new Set(entries.map(e => e.tome))].map(t => [t, `Tome ${t} — ${entries.filter(e => e.tome === t).length} unités`]), previous.tome);
    updateTome(previous.book, previous.unit);
    tome.addEventListener('change', () => updateTome());
    book.addEventListener('change', () => updateBook());
    unit.addEventListener('change', updateUnit);
    navigator.addEventListener('submit', event => {
      event.preventDefault();
      if (unit.value) location.href = unit.value;
    });
    navigator.hidden = false;
    one('.contents-fallback').open = false;
  }
  const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase().replace(/æ/g, 'ae').replace(/œ/g, 'oe');
  one('#search-form')?.addEventListener('submit', event => {
    event.preventDefault();
    const query = normalize(one('#query').value.trim());
    if (query.length < 2) return;
    const language = one('#search-language').value;
    const results = one('#search-results');
    results.replaceChildren();
    let total = 0;
    for (const record of window.ALDINES_SEARCH || []) {
      for (const lang of language === 'all' ? ['la', 'fr'] : [language]) {
        const text = record[lang];
        if (!normalize(text).includes(query)) continue;
        total++;
        if (total > 100) continue;
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = body.dataset.root + record.route + '#' + encodeURIComponent(record.anchor);
        a.textContent = `Livre ${record.book} · ${record.unit} · ${lang === 'la' ? 'Latin' : 'Français'}`;
        const p = document.createElement('p');
        p.lang = lang;
        // Les ligatures peuvent changer la longueur normalisée : le passage
        // entier est conservé au lieu de produire un extrait décalé.
        p.textContent = text;
        li.append(a, p);
        results.append(li);
      }
    }
    one('#search-status').textContent = `${total} passage(s) trouvé(s).` + (total > 100 ? ' Les 100 premiers sont affichés ; précisez votre recherche.' : '');
  });
})();
