(() => {
    async function render(container, { queryUrl, targetUrl }) {
        const viewer = new PDBeMolstarPlugin();
        const syncTheme = MineProtMolstarTheme.register(viewer);
        try {
            // Initialize the canvas before loading either structure. Mol* 3.12's
            // render() otherwise starts its customData load without awaiting it.
            await viewer.render(container, {
                alphafoldView: true,
                landscape: true,
                reactive: false,
                hideControls: false,
                sequencePanel: true,
                hideCanvasControls: [],
                bgColor: MineProtMolstarTheme.backgroundColor()
            });
            // US-align has already transformed this query into target coordinates.
            await viewer.load({ url: queryUrl, format: 'pdb', id: 'query' }, true);
            await viewer.visual.select({
                structureId: 'query',
                data: [],
                nonSelectedColor: { r: 176, g: 176, b: 176 }
            });
            // Add the target last with its default theme; keep the gray query overlay.
            await viewer.load({ url: targetUrl, format: 'mmcif', id: 'target' }, false);
            await viewer.visual.structureVisibility('target', true);
            await viewer.visual.structureVisibility('query', true);
            await viewer.visual.reset({ camera: true });
            syncTheme();
            return viewer;
        } catch (error) {
            console.error('Could not load Salign structures', error);
            if (viewer.plugin) viewer.plugin.dispose();
            container.textContent = 'Unable to load aligned structures.';
            container.setAttribute('role', 'alert');
            return null;
        }
    }

    window.MineProtSalignViewer = { render };
})();
