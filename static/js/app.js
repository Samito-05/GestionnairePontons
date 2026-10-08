/* ─── La Plage — comportements communs à toutes les pages ───────────────
   Thème · menu · toasts · dialogue de confirmation · erreurs HTMX
   horloge · comptes à rebours des sorties · service worker
   ─────────────────────────────────────────────────────────────────── */
(function () {
  'use strict';

  /* ── Thème (la valeur initiale est posée dans <head>, avant le rendu) ── */
  document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
    });
  });

  /* ── Menu déroulant (clic, pas survol — utilisable au doigt) ── */
  function closeDropdowns() {
    document.querySelectorAll('.nav-dropdown-menu.open').forEach(function (m) { m.classList.remove('open'); });
    document.querySelectorAll('.nav-dropdown-toggle').forEach(function (t) { t.setAttribute('aria-expanded', 'false'); });
  }
  document.querySelectorAll('.nav-dropdown-toggle').forEach(function (toggle) {
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      var menu = toggle.nextElementSibling;
      var wasOpen = menu.classList.contains('open');
      closeDropdowns();
      if (!wasOpen) { menu.classList.add('open'); toggle.setAttribute('aria-expanded', 'true'); }
    });
  });
  document.addEventListener('click', closeDropdowns);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeDropdowns(); });

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
    toast.className = 'toast toast-' + (kind || 'error');
    toast.innerHTML = '<span></span><button type="button" class="toast-close" aria-label="Fermer">' +
                      '<svg class="icon"><use href="#i-x"/></svg></button>';
    toast.querySelector('span').textContent = msg;
    if (options.actionLabel) {
      var action = document.createElement('button');
      action.type = 'button';
      action.className = 'btn btn-ghost btn-sm toast-action';
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
    window.showToast((d.nom || 'Embarcation') + ' — retour enregistré.', 'success', {
      actionLabel: 'Annuler',
      delay: 8000,
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
      var label = tile.querySelector('[data-state-label]');
      if (label) label.textContent = late ? 'Retard' : 'En sortie';
      if (late) {
        var lateMin = Math.floor((now - end) / 60000);
        out.innerHTML = (lateMin ? '+' + lateMin : '&lt;1') + '<small>min de retard</small>';
      } else {
        out.innerHTML = Math.max(diff, 0) + '<small>min restantes</small>';
      }
    });
  }

  /* ── Compteurs par état (puces .stat-chip[data-filter] > strong, légende du planning) ── */
  window.updateStatCounts = function () {
    var scope = document.querySelector('[data-count-scope]');
    if (!scope) return;
    var items = scope.querySelectorAll('[data-statut]');
    var n = { all: items.length, libre: 0, reservee: 0, sortie: 0, retard: 0 };
    items.forEach(function (el) {
      var s = el.dataset.statut;
      if (s in n) n[s]++;
      if (el.classList.contains('is-late')) n.retard++;
    });
    document.querySelectorAll('[data-count]').forEach(function (el) {
      el.textContent = n[el.dataset.count];
    });
    document.querySelectorAll('[data-count-alert]').forEach(function (el) {
      el.classList.toggle('is-alert', n.retard > 0);
    });
    var badge = document.getElementById('tabLateBadge');
    if (badge) { badge.hidden = n.retard === 0; badge.textContent = n.retard; }
  };

  function tick() { updateClock(); updateCountdowns(); window.updateStatCounts(); }
  tick();
  setInterval(tick, 15000);
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

  /* ── Administration mobile : l'onglet actif reste visible dans la barre défilante ── */
  var activeTab = document.querySelector('.admin-sidebar .sidebar-link.active');
  if (activeTab && activeTab.parentElement.scrollWidth > activeTab.parentElement.clientWidth) {
    var nav = activeTab.parentElement;
    nav.scrollLeft = activeTab.offsetLeft - (nav.clientWidth - activeTab.offsetWidth) / 2;
  }

  if ('serviceWorker' in navigator)
    navigator.serviceWorker.register('/static/sw.js').catch(function () {});
})();
