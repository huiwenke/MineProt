(() => {
    const root = document.documentElement;
    const viewers = new Map();

    function syncStylesheet() {
        const theme = root.dataset.theme === 'light' ? 'light' : 'dark';
        document.querySelectorAll('link[data-molstar-theme]').forEach(link => {
            const href = theme === 'light' ? link.dataset.lightHref : link.dataset.darkHref;
            if (link.getAttribute('href') !== href) link.setAttribute('href', href);
        });
    }

    function backgroundColor() {
        // The canvas palette uses six-digit hex colors, shared by both versions.
        const hex = getComputedStyle(root).getPropertyValue('--viewer-bg').trim();
        return {
            r: parseInt(hex.slice(1, 3), 16),
            g: parseInt(hex.slice(3, 5), 16),
            b: parseInt(hex.slice(5, 7), 16)
        };
    }

    function register(viewer) {
        if (viewers.has(viewer)) return viewers.get(viewer);

        function sync() {
            // 1.2.1 renders synchronously; 3.12.0 creates its canvas asynchronously.
            if (!viewer.plugin || !viewer.plugin.canvas3d) return;
            const color = backgroundColor();
            viewer.initParams.bgColor = color;
            try {
                // This changes only the renderer background, preserving the view and structure.
                Promise.resolve(viewer.canvas.setBgColor(color)).catch(error => {
                    console.error('Could not update Mol* theme', error);
                });
            } catch (error) {
                console.error('Could not update Mol* theme', error);
            }
        }

        viewers.set(viewer, sync);
        // Both bundles emit this for each loaded structure, including Salign overlays.
        viewer.events.loadComplete.subscribe(sync);
        sync();
        return sync;
    }

    document.addEventListener('mineprot:themechange', () => {
        syncStylesheet();
        viewers.forEach(sync => sync());
    });

    window.MineProtMolstarTheme = { backgroundColor, register };
    // Runs after the stylesheet link and before either plugin is instantiated.
    syncStylesheet();
})();
