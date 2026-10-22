/* ─── La Plage — comportements communs à toutes les pages ───────────────
   Toasts · dialogue de confirmation · erreurs HTMX
   horloge · comptes à rebours des sorties · bandeau des retards
   tri des tableaux · service worker
   ─────────────────────────────────────────────────────────────────── */
(function () {
  'use strict';

  /* ── Toasts ── */
  var stack = document.getElementById('toastStack');

  function dismissToast(toast) {
    if (!toast || toast.classList.contains('is-leaving')) return;
    toast.classList.add('is-leaving');
    setTimeout(function () { toast.remove(); }, 260);
  }
  function armToast(toast, delay) {
    var close = toast.querySelector('.toast-close');
    if (close) close.addEventListener('click', function () { dismissToast(toast); });
    setTimeout(function () { dismissToast(toast); }, delay);
  }
  // options : { actionLabel, onAction, delay } — bouton d'action facultatif (ex. « Annuler »)
  window.showToast = function (msg, kind, options) {
    if (!stack) return null;
    options = options || {};
    var toast = document.createElement('div');
    kind = kind || 'error';
    toast.className = 'toast toast-' + kind;
    // Même marque de balisage que les messages Django (base.html)
    var mark = { success: 'libre', info: 'sortie', warning: 'ticket', error: 'retard' }[kind] || 'sortie';
    toast.innerHTML = '<svg class="mark" aria-hidden="true"><use href="#m-' + mark + '"/></svg><span></span><button type="button" class="toast-close" aria-label="Fermer">' +
                      '<svg class="icon"><use href="#i-x"/></svg></button>';
    toast.querySelector('span').textContent = msg;
    if (options.actionLabel) {
      var action = document.createElement('button');
      action.type = 'button';
      action.className = 'toast-action';
      action.textContent = options.actionLabel;
      action.addEventListener('click', function () {
        dismissToast(toast);
        if (options.onAction) options.onAction();
      });
      toast.insertBefore(action, toast.querySelector('.toast-close'));
    }
    stack.appendChild(toast);
    armToast(toast, options.delay || (kind === 'error' ? 8000 : 5000));
    return toast;
  };
  if (stack) stack.querySelectorAll('.toast').forEach(function (t) {
    armToast(t, t.classList.contains('toast-error') ? 8000 : 5000);
  });

  /* ── Confirmation des suppressions : <form data-confirm="Titre" data-confirm-detail="…"> ── */
  var dialog = document.getElementById('confirmDialog');
  var pendingForm = null;
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form.matches || !form.matches('form[data-confirm]') || form.dataset.confirmed) return;
    e.preventDefault();
    var title  = form.dataset.confirm;
    var detail = form.dataset.confirmDetail || '';
    if (!dialog || typeof dialog.showModal !== 'function') {
      if (window.confirm(title + (detail ? '\n\n' + detail : ''))) { form.dataset.confirmed = '1'; form.submit(); }
      return;
    }
    pendingForm = form;
    dialog.querySelector('#confirmTitle').textContent = title;
    dialog.querySelector('#confirmText').textContent = detail;
    dialog.querySelector('[data-dialog-ok]').textContent = form.dataset.confirmLabel || 'Supprimer';
    dialog.showModal();
    dialog.querySelector('[data-dialog-cancel]').focus();   // focus sur l'action sûre
  });
  if (dialog) {
    dialog.querySelector('[data-dialog-cancel]').addEventListener('click', function () { dialog.close(); });
    dialog.querySelector('[data-dialog-ok]').addEventListener('click', function () {
      var form = pendingForm;
      dialog.close();
      if (form) { form.dataset.confirmed = '1'; form.submit(); }
    });
    dialog.addEventListener('click', function (e) { if (e.target === dialog) dialog.close(); });   // clic sur le fond
    dialog.addEventListener('close', function () { pendingForm = null; });
  }

  /* ── HTMX : erreurs visibles (sinon échec silencieux) ── */
  document.body.addEventListener('htmx:responseError', function (evt) {
    // 401/403 portent un HX-Redirect géré par htmx — ne pas doubler d'un toast
    if (evt.detail.xhr.getResponseHeader('HX-Redirect')) return;
    window.showToast("Erreur serveur — l'action n'a pas été prise en compte. Rechargez la page.", 'error');
  });
  document.body.addEventListener('htmx:sendError', function () {
    window.showToast('Connexion perdue — action non envoyée. Vérifiez le réseau.', 'error');
  });

  /* ── Retour validé : « Annuler » pendant quelques secondes ──
     Le serveur envoie l'événement via l'en-tête HX-Trigger (voir retour_embarcation).
     L'annulation rejoue la même cible et le même partiel que le formulaire d'origine. */
  document.body.addEventListener('retourFait', function (evt) {
    var d = evt.detail || {};
    var form = evt.target && evt.target.closest ? evt.target.closest('form') : null;
    if (!form || !d.url) return;
    var field = function (name) { var i = form.querySelector('[name="' + name + '"]'); return i ? i.value : ''; };
    var values = {
      csrfmiddlewaretoken: field('csrfmiddlewaretoken'),
      _htmx_partial: field('_htmx_partial') || 'gestionnaire',
      next: field('next') || 'gestionnaire'
    };
    // Planning : conserver la fenêtre 24h de la page (constante définie par planning.html)
    if (typeof WINDOW_START_ISO !== 'undefined') values.window_start = WINDOW_START_ISO;
    var target = form.getAttribute('hx-target');
    window.showToast('Retour enregistré : ' + (d.nom || 'embarcation'), 'success', {
      actionLabel: 'Annuler',
      delay: 15000,   // le serveur accepte l'annulation pendant 60 s
      onAction: function () {
        htmx.ajax('POST', d.url, { target: target, swap: 'outerHTML', values: values });
      }
    });
  });
  // Message libre envoyé par le serveur : HX-Trigger {"appToast": {"message": …, "kind": …}}
  document.body.addEventListener('appToast', function (evt) {
    var d = evt.detail || {};
    if (d.message) window.showToast(d.message, d.kind || 'info');
  });

  /* ── Horloge (#live-clock > [data-clock]) ── */
  function pad(n) { return String(n).padStart(2, '0'); }
  function updateClock() {
    var now = new Date();
    var txt = pad(now.getHours()) + ':' + pad(now.getMinutes());
    document.querySelectorAll('[data-clock]').forEach(function (el) { el.textContent = txt; });
  }

  /* ── Comptes à rebours : tuiles .tile[data-end] (fin prévue, ms epoch) ──
     Tient « reste N min » / « +N min » à jour entre deux réponses serveur,
     et bascule la tuile en retard dès que l'heure prévue est passée. */
  var skewEl = document.querySelector('[data-server-now]');
  // Écart horloge appareil / serveur : un téléphone mal réglé ne fausse pas les retards
  var clockSkew = skewEl ? parseInt(skewEl.dataset.serverNow, 10) * 1000 - Date.now() : 0;
  if (Math.abs(clockSkew) < 5000) clockSkew = 0;

  function updateCountdowns() {
    var now = Date.now() + clockSkew;
    document.querySelectorAll('.tile[data-end]').forEach(function (tile) {
      var end = parseInt(tile.dataset.end, 10);
      var out = tile.querySelector('[data-remaining]');
      if (!end || !out) return;
      var diff = Math.round((end - now) / 60000);
      var late = now > end;
      tile.classList.toggle('is-late', late);
      if (late) {
        var lateMin = Math.floor((now - end) / 60000);
        out.textContent = lateMin ? '+' + lateMin + ' min' : '+<1 min';
      } else {
        out.textContent = 'reste ' + Math.max(diff, 0) + ' min';
      }
    });
  }

  /* ── Compteurs par état (filtres [data-count], légende du planning) ── */
  window.updateStatCounts = function () {
    var scope = document.querySelector('[data-count-scope]');
    if (!scope) return;
    var items = scope.querySelectorAll('[data-statut]');
    var n = { all: items.length, libre: 0, reservee: 0, sortie: 0, retard: 0 };
    var firstLate = null;
    items.forEach(function (el) {
      var s = el.dataset.statut;
      if (s in n) n[s]++;
      if (el.classList.contains('is-late')) { n.retard++; if (!firstLate) firstLate = el; }
    });
    document.querySelectorAll('[data-count]').forEach(function (el) {
      el.textContent = n[el.dataset.count];
    });
    document.querySelectorAll('[data-count-alert]').forEach(function (el) {
      el.classList.toggle('is-alert', n.retard > 0);
    });
    var badge = document.getElementById('tabLateBadge');
    if (badge) { badge.hidden = n.retard === 0; badge.textContent = n.retard; }

    // Bandeau des retards : le premier en clair, les suivants comptés
    var band = document.querySelector('[data-late-band]');
    if (band) {
      band.hidden = !firstLate;
      document.body.classList.toggle('has-late-band', !!firstLate);   // le toast passe sous le bandeau
      if (firstLate) {
        var name = firstLate.querySelector('.tile-name');
        var fig = firstLate.querySelector('[data-remaining]');
        var txt = (name ? name.textContent.trim() : '') + (fig ? ' ' + fig.textContent.trim() : '');
        if (n.retard > 1) txt += ' · ' + (n.retard - 1) + ' autre' + (n.retard > 2 ? 's' : '');
        band.querySelector('[data-late-text]').textContent = txt;
      }
    }
  };

  /* ── Retards en tête de leur ponton : déplacés dans le DOM (pas en CSS)
     pour que l'ordre du clavier et des lecteurs d'écran suive l'écran ── */
  var lastPointer = 0;
  document.addEventListener('pointerdown', function () { lastPointer = Date.now(); }, true);
  function liftLateRows() {
    // Jamais pendant qu'un doigt vise une ligne : on attend le tick suivant
    if (Date.now() - lastPointer < 8000) return;
    document.querySelectorAll('.rows').forEach(function (rows) {
      var firstOnTime = null;
      Array.prototype.forEach.call(rows.children, function (el) {
        if (!el.classList.contains('tile')) return;
        if (!el.classList.contains('is-late')) { if (!firstOnTime) firstOnTime = el; return; }
        // Ne jamais déplacer la ligne sous le doigt / le focus
        if (firstOnTime && !el.contains(document.activeElement)) rows.insertBefore(el, firstOnTime);
      });
    });
  }

  function tick() { updateClock(); updateCountdowns(); liftLateRows(); window.updateStatCounts(); }
  tick();
  setInterval(function () { if (!document.hidden) tick(); }, 15000);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) tick(); });
  document.body.addEventListener('htmx:afterSwap', tick);
  window.refreshLiveUi = tick;

  /* ── Mot de passe : afficher / masquer ── */
  document.querySelectorAll('[data-password-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var input = btn.parentElement.querySelector('input');
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.setAttribute('aria-pressed', show ? 'true' : 'false');
      btn.setAttribute('aria-label', show ? 'Masquer le mot de passe' : 'Afficher le mot de passe');
    });
  });

  /* ── Tableaux triables : <table data-sortable>, <th data-sort="text|num"> ──
     Tri côté client de la page affichée ; l'ordre serveur revient au rechargement. */
  var collator = new Intl.Collator('fr', { numeric: true, sensitivity: 'base' });
  document.querySelectorAll('table[data-sortable]').forEach(function (table) {
    var tbody = table.tBodies[0];
    table.querySelectorAll('th[data-sort]').forEach(function (th, _, all) {
      var idx = Array.prototype.indexOf.call(th.parentElement.children, th);
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'th-sort';
      btn.innerHTML = '<span></span><svg class="icon" aria-hidden="true"><use href="#i-sort"/></svg>';
      btn.firstChild.textContent = th.textContent.trim();
      th.textContent = '';
      th.appendChild(btn);
      btn.addEventListener('click', function () {
        var dir = th.getAttribute('aria-sort') === 'ascending' ? 'descending' : 'ascending';
        all.forEach(function (o) { o.removeAttribute('aria-sort'); });
        th.setAttribute('aria-sort', dir);
        var num = th.dataset.sort === 'num', sign = dir === 'ascending' ? 1 : -1;
        // Clé lue une seule fois par ligne
        var keyed = Array.prototype.filter.call(tbody.rows, function (r) { return !r.classList.contains('empty-row'); })
          .map(function (r) {
            var td = r.children[idx];
            var v = td ? (td.dataset.value || td.textContent).trim() : '';
            return { r: r, k: num ? parseFloat(v.replace(',', '.')) || 0 : v };
          });
        keyed.sort(function (a, b) { return sign * (num ? a.k - b.k : collator.compare(a.k, b.k)); });
        keyed.forEach(function (o) { tbody.appendChild(o.r); });
      });
    });
  });

  /* ── Administration mobile : l'onglet actif reste visible dans la barre défilante ── */
  var activeTab = document.querySelector('.admin-sidebar .sidebar-link.active');
  if (activeTab && activeTab.parentElement.scrollWidth > activeTab.parentElement.clientWidth) {
    var nav = activeTab.parentElement;
    nav.scrollLeft = activeTab.offsetLeft - (nav.clientWidth - activeTab.offsetWidth) / 2;
  }

  if ('serviceWorker' in navigator)
    navigator.serviceWorker.register('/static/sw.js').catch(function () {});
})();
