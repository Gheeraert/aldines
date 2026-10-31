/* Aucun service distant, aucun suivi, aucune dépendance JavaScript. */
(() => {
  'use strict';
  const one = s => document.querySelector(s);
  const body = document.body;
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
    const toolbarBottom = one('.reader-tools')?.getBoundingClientRect().bottom || 0;
    const visible = rows.find(r => r.getBoundingClientRect().bottom > toolbarBottom);
    const offset = visible?.getBoundingClientRect().top;
    body.dataset.mode = mode;
    if (visible) window.scrollBy(0, visible.getBoundingClientRect().top - offset);
  }
  one('#reading-mode')?.addEventListener('change', e => changeMode(e.target.value));
  one('#reader-options')?.addEventListener('click', e => {
    const panel = one('#display-options');
    panel.hidden = !panel.hidden;
    e.target.setAttribute('aria-expanded', String(!panel.hidden));
  });
  document.querySelectorAll('[data-option]').forEach(input => input.addEventListener('change', () => {
    body.classList.toggle('hide-' + input.dataset.option, !input.checked);
  }));
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
