(() => {
    'use strict';
    const tabs = [...document.querySelectorAll('[data-tab]')];
    function selectTab(tab) {
        tabs.forEach(item => {
            const selected = item === tab;
            item.setAttribute('aria-selected', String(selected));
            item.tabIndex = selected ? 0 : -1;
            document.getElementById(`panel-${item.dataset.tab}`).hidden = !selected;
        });
    }
    tabs.forEach((tab, index) => {
        tab.addEventListener('click', () => selectTab(tab));
        tab.addEventListener('keydown', event => {
            if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault();
            const next = event.key === 'Home' ? tabs[0] : event.key === 'End' ? tabs[tabs.length - 1] : tabs[(index + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
            selectTab(next);
            next.focus();
        });
    });
    const system = document.getElementById('archive-system');
    const autoAnnotate = document.querySelector('#colabfold-options [name="annotate"]');
    const archiveAnnotations = document.getElementById('archive-annotations');
    function updateArchiveAnnotations() {
        const automatic = system.value === 'colabfold' && autoAnnotate.checked;
        archiveAnnotations.hidden = archiveAnnotations.disabled = automatic;
    }
    autoAnnotate.addEventListener('change', updateArchiveAnnotations);
    function updateSystem() {
        const colabfold = system.value === 'colabfold';
        const options = document.getElementById('colabfold-options');
        options.hidden = options.disabled = !colabfold;
        updateArchiveAnnotations();
        document.getElementById('archive-system-hint').textContent = colabfold
            ? 'ColabFold: rank 1 PDB and scores JSON. Include matching A3M files when automatic annotation is enabled.'
            : 'AlphaFold3: model CIF and matching confidence / summary JSON, including result subdirectories.';
    }
    system.addEventListener('change', updateSystem);
    updateSystem();
    ['single', 'archive'].forEach(prefix => {
        const homolog = document.getElementById(`${prefix}-homolog`);
        const database = document.getElementById(`${prefix}-database`);
        function updateHomolog() {
            database.disabled = !homolog.value.trim();
            if (database.disabled) database.value = '';
        }
        homolog.addEventListener('input', updateHomolog);
        updateHomolog();
    });
    document.querySelectorAll('.import-upload').forEach(area => {
        const input = area.querySelector('input[type="file"]');
        const status = area.querySelector('.import-file-status');
        const clear = area.querySelector('.salign-clear-file');
        const initial = status.textContent;
        function update() {
            const file = input.files[0];
            status.textContent = file ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB` : initial;
            clear.hidden = !file;
        }
        input.addEventListener('change', update);
        clear.addEventListener('click', () => { input.value = ''; update(); });
        ['dragenter', 'dragover'].forEach(type => area.addEventListener(type, event => {
            event.preventDefault(); area.classList.add('is-dragging');
        }));
        area.addEventListener('dragleave', event => {
            if (!area.contains(event.relatedTarget)) area.classList.remove('is-dragging');
        });
        area.addEventListener('drop', event => {
            event.preventDefault(); area.classList.remove('is-dragging');
            if (event.dataTransfer.files.length !== 1) {
                status.textContent = 'Please select one file.'; return;
            }
            input.files = event.dataTransfer.files; update();
        });
    });
    document.querySelectorAll('.import-form').forEach(form => form.addEventListener('submit', async event => {
        event.preventDefault();
        const result = document.getElementById('import-result');
        const status = document.getElementById('import-status');
        const list = document.getElementById('import-results');
        result.hidden = false; list.replaceChildren();
        const payload = new FormData(form);
        const size = [...payload.values()].reduce((sum, value) => sum + (value instanceof File ? value.size : 0), 0);
        if (size + 8192 > Number(form.dataset.maxBytes)) {
            status.textContent = 'Total upload exceeds the server size limit.'; return;
        }
        const button = form.querySelector('button[type="submit"]');
        button.disabled = true;
        status.textContent = 'Uploading and processing… Please keep this page open.';
        try {
            const response = await fetch(form.action, {method: 'POST', body: payload});
            if (!response.ok) throw new Error(await response.text());
            const body = await response.json();
            const failures = body.results.filter(item => item.status !== 'imported').length;
            status.textContent = failures ? `Finished with ${failures} failed model(s). Review the results below.` : `Imported ${body.results.length} model(s).`;
            body.results.forEach(item => {
                const row = document.createElement('li');
                row.textContent = `${item.name}: ${item.status}${item.error ? ' — ' + item.error : ''}`;
                if (item.status === 'imported') {
                    const link = document.createElement('a');
                    link.href = '/browse.php?' + new URLSearchParams({repo: payload.get('repo').trim()});
                    link.textContent = ' Browse repository'; row.append(link);
                }
                list.append(row);
            });
        } catch (error) {
            status.textContent = `Import did not complete: ${error.message}. Completed files may remain; review the repository before retrying.`;
        } finally { button.disabled = false; }
    }));
})();
