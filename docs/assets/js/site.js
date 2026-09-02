/* The only script the site runs: the menu groups, the drawer the menu
 * becomes on a narrow screen, and the theme toggle. Nothing here is needed
 * to read a page - every one of them works with the script left out. */

(function () {
  'use strict';

  var root = document.documentElement;
  var STORAGE_KEY = 'py_maze-theme';

  /* ---- Theme -------------------------------------------------------- */

  function preferredTheme() {
    // what the reader is being shown right now, whether that came from
    // their own choice or from the operating system
    var chosen = root.getAttribute('data-theme');
    if (chosen === 'light' || chosen === 'dark') {
      return chosen;
    }

    return window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  }

  function paintThemeButton(button) {
    var dark = preferredTheme() === 'dark';
    var label = button.querySelector('.theme-button-text');

    // the button says what pressing it will do, rather than what is on
    if (label) {
      label.textContent = dark ? 'Light' : 'Dark';
    }
    button.setAttribute('aria-pressed', dark ? 'true' : 'false');
    button.setAttribute('aria-label',
      dark ? 'Switch to the light theme' : 'Switch to the dark theme');
  }

  var themeButton = document.querySelector('.theme-button');
  if (themeButton) {
    paintThemeButton(themeButton);

    themeButton.addEventListener('click', function () {
      var next = preferredTheme() === 'dark' ? 'light' : 'dark';

      root.setAttribute('data-theme', next);
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch (error) {
        // storage can be refused; the choice then lasts this page only
      }
      paintThemeButton(themeButton);
    });
  }

  /* ---- Menu groups -------------------------------------------------- */

  var groups = document.querySelectorAll('.menu-group');
  Array.prototype.forEach.call(groups, function (group) {
    var button = group.querySelector('.menu-group-button');
    if (!button) {
      return;
    }

    button.addEventListener('click', function () {
      var open = group.classList.toggle('is-open');
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });

  /* ---- The drawer --------------------------------------------------- */

  var menu = document.getElementById('menu');
  var menuButton = document.querySelector('.menu-button');
  var veil = document.querySelector('.menu-veil');

  function showMenu(open) {
    if (!menu || !menuButton) {
      return;
    }

    menu.classList.toggle('is-open', open);
    menuButton.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (veil) {
      veil.hidden = !open;
    }
  }

  if (menuButton) {
    menuButton.addEventListener('click', function () {
      showMenu(!menu.classList.contains('is-open'));
    });
  }

  if (veil) {
    veil.addEventListener('click', function () {
      showMenu(false);
    });
  }

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && menu && menu.classList.contains('is-open')) {
      showMenu(false);
      menuButton.focus();
    }
  });

  // following a link inside the drawer leaves it open behind the new page
  // on browsers that restore the scroll position, so close it on the way
  if (menu) {
    menu.addEventListener('click', function (event) {
      if (event.target.closest('.menu-link')) {
        showMenu(false);
      }
    });
  }
})();
