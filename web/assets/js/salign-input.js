(() => {
    'use strict';
    const area = document.getElementById('salign-structure-input');
    if (!area) return;
    const input = document.getElementById('salign-file');
    const text = document.getElementById('salign-structure');
    const choose = document.getElementById('salign-choose-file');
    const clear = document.getElementById('salign-clear-file');
    const status = document.getElementById('salign-file-status');
    const submit = document.getElementById('salign-submit');
    const limit = Number(area.dataset.maxBytes);
    let version = 0, loading = false, dragDepth = 0;
    const idleMessage = 'No file selected. Drop a file, choose one, or paste structure text below.';

    function show(message, state = '') {
        status.textContent = message;
        status.classList.toggle('is-error', state === 'error');
        status.classList.toggle('is-loaded', state === 'loaded');
        clear.hidden = !text.value && !loading;
    }
    function busy(value) {
        loading = value;
        area.setAttribute('aria-busy', String(value));
        submit.disabled = value;
        clear.hidden = !text.value && !value;
    }
    function sizeLabel(size) {
        return size < 1024 * 1024 ? `${(size / 1024).toFixed(1)} KB` : `${(size / 1024 / 1024).toFixed(1)} MB`;
    }
    async function loadFiles(files) {
        const current = ++version;
        busy(false);
        // Cancel a previous read even when the replacement selection is invalid.
        if (files.length !== 1) {
            show('Please choose one PDB or CIF file at a time. Existing text was kept.', 'error');
            return;
        }
        const file = files[0];
        if (!/\.(pdb|cif|mmcif)$/i.test(file.name)) {
            show('Choose a .pdb, .cif or .mmcif file. Existing text was kept.', 'error');
            return;
        }
        if (!file.size || file.size > limit) {
            show(file.size ? `File is too large. Maximum size: ${sizeLabel(limit)}. Existing text was kept.` :
                'This file is empty. Existing text was kept.', 'error');
            return;
        }
        busy(true);
        show(`Reading ${file.name}…`);
        try {
            const bytes = await file.arrayBuffer();
            if (current !== version) return;
            const content = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
            if (content.includes('\0') || !(/^(?:ATOM  |HETATM)/m.test(content) || /^\s*_atom_site\./m.test(content))) {
                throw new Error('No PDB atom records or CIF atom-site fields were found in this file.');
            }
            // Keep the existing textarea-based API: the file is loaded locally,
            // and only the visible, editable text is submitted with Search.
            text.value = content;
            text.dispatchEvent(new Event('change', { bubbles: true }));
            show(`${file.name} · ${sizeLabel(file.size)} · Ready to search`, 'loaded');
        } catch (error) {
            if (current !== version) return;
            console.error('Could not read query structure', error);
            show(`Could not load this structure. Check that it is a UTF-8 PDB or CIF file with atom coordinates. Existing text was kept.`, 'error');
        } finally {
            if (current === version) busy(false);
        }
    }
    choose.hidden = false;
    show(text.value ? 'Structure text is ready to search.' : idleMessage);
    choose.addEventListener('click', () => input.click());
    input.addEventListener('change', () => {
        const files = Array.from(input.files || []);
        input.value = ''; // Allow choosing the same file again after editing or clearing.
        if (files.length) loadFiles(files);
    });
    clear.addEventListener('click', () => {
        ++version;
        busy(false);
        input.value = '';
        text.value = '';
        show(idleMessage);
        text.focus();
    });
    text.addEventListener('input', () => {
        ++version; // An in-flight file read must never overwrite newly pasted/edited text.
        busy(false);
        input.value = '';
        show(text.value.trim() ? 'Structure text edited · Ready to search' : idleMessage);
    });
    const hasFiles = event => Array.from(event.dataTransfer?.types || []).includes('Files');
    function resetDrag() {
        dragDepth = 0;
        area.classList.remove('is-dragging');
    }
    area.addEventListener('dragenter', event => {
        if (!hasFiles(event)) return;
        event.preventDefault();
        dragDepth++;
        area.classList.add('is-dragging');
    });
    area.addEventListener('dragover', event => {
        if (!hasFiles(event)) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = 'copy';
    });
    area.addEventListener('dragleave', () => {
        dragDepth = Math.max(0, dragDepth - 1);
        if (!dragDepth) area.classList.remove('is-dragging');
    });
    area.addEventListener('drop', event => {
        if (!hasFiles(event)) return;
        event.preventDefault();
        resetDrag();
        loadFiles(Array.from(event.dataTransfer.files));
    });
    // Dropping outside the card should not navigate away and lose the form.
    document.addEventListener('dragover', event => {
        if (!hasFiles(event) || area.contains(event.target)) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = 'none';
    });
    document.addEventListener('drop', event => {
        if (!hasFiles(event) || area.contains(event.target)) return;
        event.preventDefault();
        resetDrag();
        show('Drop the file inside the Query structure area above.', 'error');
    });
    window.addEventListener('dragend', resetDrag);
    window.addEventListener('blur', resetDrag);
    document.getElementById('salign-form').addEventListener('submit', event => {
        if (loading) {
            event.preventDefault();
            show('Please wait for the structure file to finish loading.');
        }
    });
})();
