(() => {
    const storageKey = 'mineprot-theme';
    const root = document.documentElement;

    function applyTheme(value) {
        const theme = value === 'light' ? 'light' : 'dark';
        root.dataset.theme = theme;
        const label = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
        document.querySelectorAll('[data-theme-toggle]').forEach(button => {
            button.setAttribute('aria-label', label);
            button.title = label;
        });
        document.dispatchEvent(new CustomEvent('mineprot:themechange', { detail: { theme } }));
    }

    let savedTheme;
    let themeStorage;
    try {
        themeStorage = window.localStorage;
        savedTheme = themeStorage.getItem(storageKey);
    } catch (_) {
        // Theme switching still works when browser storage is unavailable.
    }
    // Loaded synchronously in <head> so the first paint uses the saved theme.
    applyTheme(savedTheme);
    document.addEventListener('DOMContentLoaded', () => applyTheme(root.dataset.theme));

    document.addEventListener('click', event => {
        if (!(event.target instanceof Element) || !event.target.closest('[data-theme-toggle]')) return;
        const theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
        applyTheme(theme);
        try {
            if (themeStorage) themeStorage.setItem(storageKey, theme);
        } catch (_) {
            // Keep the selected theme for the current page.
        }
    });

    window.addEventListener('storage', event => {
        if (event.storageArea === themeStorage && (event.key === storageKey || event.key === null)) {
            applyTheme(event.newValue);
        }
    });
})();
