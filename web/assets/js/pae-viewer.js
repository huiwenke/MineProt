/* PAE indices are zero-based; all displayed positions are one-based.
 * matrix[aligned][scored]: rows are reference frames, columns are scored tokens.
 */
(() => {
    'use strict';
    const data = JSON.parse(document.getElementById('pae-data').textContent);
    const matrix = data.matrix;
    const n = matrix.length;
    const residues = data.residues;
    const mapped = residues.length === n;
    const $ = id => document.getElementById(id);
    const canvas = $('pae-canvas');
    const overlay = $('pae-overlay');
    const sequence = $('pae-sequence');
    const host = $('pae-structure');
    const tooltip = $('pae-tooltip');
    const colors = { x: '#26a6cf', y: '#f6c344', both: '#bd83e5' };
    const svgNS = 'http://www.w3.org/2000/svg';
    const buttons = [];
    const chainBoundaries = mapped ? residues.flatMap((r, i) =>
        i > 0 && r.chain !== residues[i - 1].chain ? [i] : []) : [];
    const indexBySelection = new Map();
    const selectionKey = (chain, namespace, seq, ins = '', atom = '') =>
        JSON.stringify([chain, namespace, String(seq), ins || '', atom || '']);
    function registerIndex(key, i) {
        if (!indexBySelection.has(key)) indexBySelection.set(key, new Set());
        indexBySelection.get(key).add(i);
    }
    let viewer, ready = false, selection = null, hover = null, drag = null;
    let keyboardPoint = { x: 0, y: 0 };
    let hoverFrame = 0, pendingHighlight = null;
    let updateVersion = 0, viewerQueue = Promise.resolve();
    let highlightedButtons = [];

    function warning(message) {
        const node = $('pae-warning');
        if (!node.textContent.includes(message)) node.textContent += (node.textContent ? ' ' : '') + message;
        node.hidden = false;
    }
    if (data.warning) warning(data.warning);
    $('pae-summary').textContent = `${n.toLocaleString()} token positions · PAE in ångströms` +
        (n > 1800 ? ' · Display sampled; inspected values use the full matrix' : '');
    $('pae-length').textContent = `${n} × ${n}`;
    overlay.setAttribute('viewBox', `0 0 ${n} ${n}`);

    function label(i) {
        if (!mapped) return `Position ${i + 1}`;
        const r = residues[i];
        const author = r.auth_seq ? `${r.auth_chain}:${r.auth_seq}${r.ins}` : `${r.chain}:${r.seq}`;
        const atom = r.atom ? ` / ${r.atom}` : '';
        return `${author} ${r.comp}${atom} (token ${i + 1})${r.observed ? '' : ' · ' + (r.reason || 'no coordinates')}`;
    }
    function rangeLabel(range) {
        return range[0] === range[1] ? label(range[0]) : `${label(range[0])} → ${label(range[1])}`;
    }
    const inRange = (i, range) => range && i >= range[0] && i <= range[1];
    const normalized = (a, b) => [Math.min(a, b), Math.max(a, b)];
    const pairSelection = (a, b) => ({ x: normalized(a.x, b.x), y: normalized(a.y, b.y) });
    const paeValue = (x, y) => `${matrix[y][x].toFixed(2)} Å`;

    // A small raster avoids allocating an N² collection of chart point objects.
    // Large matrices are sampled for display only; inspection uses original data.
    const palette = [[0, 69, 41], [39, 139, 80], [123, 200, 124], [214, 237, 201], [247, 252, 245]];
    function colorAt(value) {
        const t = Math.max(0, Math.min(1, value / data.maximum)) * (palette.length - 1);
        const p = Math.min(palette.length - 2, Math.floor(t));
        const f = t - p;
        return palette[p].map((v, k) => Math.round(v + f * (palette[p + 1][k] - v)));
    }
    const rasterSize = Math.min(n, 1800);
    canvas.width = canvas.height = rasterSize;
    const context = canvas.getContext('2d');
    if (!context) {
        warning('The browser could not initialize the PAE canvas.');
        return;
    }
    const image = context.createImageData(rasterSize, rasterSize);
    for (let y = 0; y < rasterSize; y++) {
        const aligned = Math.min(n - 1, Math.floor((y + .5) * n / rasterSize));
        for (let x = 0; x < rasterSize; x++) {
            const scored = Math.min(n - 1, Math.floor((x + .5) * n / rasterSize));
            const offset = (y * rasterSize + x) * 4;
            image.data.set(colorAt(matrix[aligned][scored]), offset);
            image.data[offset + 3] = 255;
        }
    }
    context.putImageData(image, 0, 0);
    for (let i = 0; i <= 4; i++) {
        const tick = document.createElement('span');
        tick.textContent = (data.maximum * i / 4).toFixed(i === 0 ? 0 : 1);
        $('pae-scale-ticks').append(tick);
    }
    const ticks = [...new Set([0, Math.round((n - 1) / 4), Math.round((n - 1) / 2), Math.round(3 * (n - 1) / 4), n - 1])];
    ticks.forEach(i => {
        const x = document.createElement('span');
        x.textContent = i + 1;
        x.style.left = `${(i + .5) / n * 100}%`;
        $('pae-x-ticks').append(x);
        const y = document.createElement('span');
        y.textContent = i + 1;
        y.style.top = `${(i + .5) / n * 100}%`;
        $('pae-y-ticks').append(y);
    });

    function svg(tag, attrs) {
        const element = document.createElementNS(svgNS, tag);
        Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
        overlay.append(element);
        return element;
    }
    function line(x1, y1, x2, y2, color, width = 1) {
        svg('line', { x1, y1, x2, y2, stroke: color, 'stroke-width': width, 'vector-effect': 'non-scaling-stroke' });
    }
    function paintOverlay(active = selection) {
        overlay.replaceChildren();
        chainBoundaries.forEach(i => {
            line(i, 0, i, n, '#8889');
            line(0, i, n, i, '#8889');
        });
        if (active) {
            const [x0, x1] = active.x, [y0, y1] = active.y;
            svg('rect', { x: x0, y: y0, width: x1 - x0 + 1, height: y1 - y0 + 1,
                fill: '#ffffff30', stroke: colors.both, 'stroke-width': 2, 'vector-effect': 'non-scaling-stroke' });
            line(x0, 0, x1 + 1, 0, colors.x, 5);
            line(0, y0, 0, y1 + 1, colors.y, 5);
        }
        if (hover) {
            line(hover.x + .5, 0, hover.x + .5, n, '#ec642c', 1.5);
            line(0, hover.y + .5, n, hover.y + .5, '#ec642c', 1.5);
        }
    }
    function paintSequence(active = selection) {
        buttons.forEach((button, i) => {
            button.classList.toggle('is-x', !!active && inRange(i, active.x));
            button.classList.toggle('is-y', !!active && inRange(i, active.y));
        });
    }
    function paintHover() {
        highlightedButtons.forEach(button => button.classList.remove('is-hover'));
        highlightedButtons = [];
        if (!mapped || !hover) return;
        [...new Set([hover.x, hover.y])].forEach(i => {
            buttons[i].classList.add('is-hover');
            highlightedButtons.push(buttons[i]);
        });
    }
    function queryFor(i) {
        return { ...residues[i].query };
    }
    function highlight(point) {
        pendingHighlight = point;
        if (hoverFrame) return;
        hoverFrame = requestAnimationFrame(() => {
            hoverFrame = 0;
            if (!ready || !mapped) return;
            const point = pendingHighlight;
            const queries = point ? [...new Set([point.x, point.y])].filter(i => residues[i].observed).map(queryFor) : [];
            const operation = queries.length ? viewer.visual.highlight({ data: queries }) : viewer.visual.clearHighlight();
            Promise.resolve(operation).catch(error => console.error('PAE highlight failed', error));
        });
    }
    function inspect(point, notifyViewer = true) {
        hover = point;
        if (point) {
            keyboardPoint = point;
            $('pae-hover').textContent = `Scored: ${label(point.x)} · Aligned/reference: ${label(point.y)} · PAE ${paeValue(point.x, point.y)}`;
        }
        paintOverlay(drag ? drag.preview : selection);
        paintHover();
        if (notifyViewer) highlight(point);
    }
    function selectionQueries(active) {
        const queries = [];
        let last = null;
        // Merge adjacent label positions to keep Mol* selection updates small.
        residues.forEach((r, i) => {
            const x = inRange(i, active.x), y = inRange(i, active.y);
            if (!r.observed || !r.query || (!x && !y)) { last = null; return; }
            const color = x && y ? colors.both : x ? colors.x : colors.y;
            if (r.atom || r.seq === null) {
                queries.push({ ...r.query, color, opacity: 1 });
                last = null;
                return;
            }
            if (last && last.label_asym_id === r.chain && last.color === color && last.end_label_seq_id + 1 === r.seq) {
                last.end_label_seq_id = r.seq;
            } else {
                last = { label_asym_id: r.chain, beg_label_seq_id: r.seq, end_label_seq_id: r.seq, color, opacity: 1 };
                queries.push(last);
            }
        });
        return queries;
    }
    function updateViewer(focus) {
        const version = ++updateVersion;
        const active = selection;
        // Serialize state changes; a stale operation must never overwrite a newer selection.
        viewerQueue = viewerQueue.catch(() => {}).then(async () => {
            if (!ready || !mapped || version !== updateVersion) return;
            await viewer.visual.clearHighlight();
            if (!active) {
                await viewer.visual.clearSelection();
                return;
            }
            const queries = selectionQueries(active);
            if (!queries.length) {
                await viewer.visual.clearSelection();
                return;
            }
            await viewer.visual.select({ data: queries, nonSelectedOpacity: .28 });
            if (focus && version === updateVersion) await viewer.visual.focus(queries);
        }).catch(error => {
            console.error('PAE selection failed', error);
            warning('A structure selection could not be applied. Try clearing the selection.');
        });
    }
    function commit(active, focus = true) {
        selection = active;
        hover = null;
        highlight(null);
        tooltip.hidden = true;
        paintOverlay();
        paintSequence();
        paintHover();
        if (!active) {
            $('pae-selection').textContent = 'No selection. Select a token pair or drag a box in the PAE plot.';
        } else {
            const pair = active.x[0] === active.x[1] && active.y[0] === active.y[1];
            $('pae-selection').textContent = `Scored: ${rangeLabel(active.x)} · Reference: ${rangeLabel(active.y)}` +
                (pair ? ` · PAE ${paeValue(active.x[0], active.y[0])}` : ' · Cyan: scored / yellow: reference / purple: overlap');
        }
        updateViewer(focus);
    }

    function pointAt(event) {
        const bounds = canvas.getBoundingClientRect();
        return {
            x: Math.max(0, Math.min(n - 1, Math.floor((event.clientX - bounds.left) / bounds.width * n))),
            y: Math.max(0, Math.min(n - 1, Math.floor((event.clientY - bounds.top) / bounds.height * n))),
        };
    }
    function showTooltip(event, point) {
        tooltip.textContent = `Scored: ${label(point.x)}\nReference: ${label(point.y)}\nPAE ${paeValue(point.x, point.y)}`;
        tooltip.hidden = false;
        const bounds = canvas.getBoundingClientRect();
        tooltip.style.left = `${Math.max(0, Math.min(bounds.width - tooltip.offsetWidth, event.clientX - bounds.left + 15))}px`;
        tooltip.style.top = `${Math.max(0, Math.min(bounds.height - tooltip.offsetHeight, event.clientY - bounds.top + 15))}px`;
    }
    canvas.addEventListener('pointerdown', event => {
        if (!event.isPrimary || event.button !== 0) return;
        canvas.focus({ preventScroll: true });
        const point = pointAt(event);
        drag = { source: 'plot', pointer: event.pointerId, start: point, preview: pairSelection(point, point) };
        canvas.setPointerCapture(event.pointerId);
        event.preventDefault();
    });
    canvas.addEventListener('pointermove', event => {
        const point = pointAt(event);
        if (drag?.source === 'plot') {
            drag.preview = pairSelection(drag.start, point);
            hover = point;
            paintOverlay(drag.preview);
            paintSequence(drag.preview);
            tooltip.hidden = true;
        } else {
            inspect(point);
            showTooltip(event, point);
        }
    });
    canvas.addEventListener('pointerup', event => {
        if (drag?.source !== 'plot' || drag.pointer !== event.pointerId) return;
        const active = pairSelection(drag.start, pointAt(event));
        drag = null;
        canvas.releasePointerCapture(event.pointerId);
        commit(active);
    });
    canvas.addEventListener('pointerleave', () => {
        if (drag) return;
        tooltip.hidden = true;
        inspect(null);
    });
    canvas.addEventListener('keydown', event => {
        const steps = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
        if (steps[event.key]) {
            event.preventDefault();
            const [dx, dy] = steps[event.key];
            inspect({ x: Math.max(0, Math.min(n - 1, keyboardPoint.x + dx)), y: Math.max(0, Math.min(n - 1, keyboardPoint.y + dy)) });
        } else if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            commit(pairSelection(keyboardPoint, keyboardPoint));
        }
    });

    if (mapped) {
        let chain, container;
        const fragment = document.createDocumentFragment();
        residues.forEach((r, i) => {
            if (chain !== r.chain) {
                chain = r.chain;
                const row = document.createElement('div');
                row.className = 'pae-chain';
                const label = document.createElement('span');
                label.className = 'pae-chain-label';
                const kindLabel = { protein: 'Protein', dna: 'DNA', rna: 'RNA', ion: 'Ion', ligand: 'Ligand', polymer: 'Polymer' };
                label.textContent = `${r.auth_chain || chain} · ${kindLabel[r.kind] || 'Tokens'}`;
                container = document.createElement('div');
                container.className = 'pae-chain-residues';
                row.append(label, container);
                fragment.append(row);
            }
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'pae-residue' + (r.observed ? '' : ' is-missing') + (r.atom ? ' is-atom' : '');
            button.dataset.index = i;
            button.textContent = r.display || r.letter;
            button.title = label(i);
            button.setAttribute('aria-label', label(i));
            button.tabIndex = i === 0 ? 0 : -1;
            if (i === 0 || residues[i - 1].chain !== chain || (i + 1) % 10 === 0) button.dataset.tick = i + 1;
            buttons.push(button);
            container.append(button);
            if (r.observed && r.query) {
                if (r.seq !== null) registerIndex(selectionKey(r.chain, 'label', r.seq, '', r.atom), i);
                if (r.auth_seq !== '') registerIndex(selectionKey(r.chain, 'auth', r.auth_seq, r.ins, r.atom), i);
            }
        });
        sequence.append(fragment);
    } else {
        sequence.textContent = 'A matching token map is unavailable. You can still inspect and select regions in the PAE plot.';
    }
    function sequenceIndex(event) {
        const target = document.elementFromPoint(event.clientX, event.clientY)?.closest('.pae-residue');
        return target && sequence.contains(target) ? Number(target.dataset.index) : null;
    }
    sequence.addEventListener('pointerdown', event => {
        if (!event.isPrimary || event.button !== 0) return;
        const i = sequenceIndex(event);
        if (i === null) return;
        event.preventDefault();
        buttons[i].focus({ preventScroll: true });
        drag = { source: 'sequence', pointer: event.pointerId, start: i, end: i,
            preview: { x: [i, i], y: [i, i] } };
        sequence.setPointerCapture(event.pointerId);
    });
    sequence.addEventListener('pointermove', event => {
        const i = sequenceIndex(event);
        if (i === null) return;
        if (drag?.source === 'sequence') {
            drag.end = i;
            const range = normalized(drag.start, i);
            drag.preview = { x: range, y: range };
            hover = null;
            paintOverlay(drag.preview);
            paintSequence(drag.preview);
        } else inspect({ x: i, y: i });
    });
    sequence.addEventListener('pointerup', event => {
        if (drag?.source !== 'sequence' || drag.pointer !== event.pointerId) return;
        const range = normalized(drag.start, sequenceIndex(event) ?? drag.end);
        drag = null;
        sequence.releasePointerCapture(event.pointerId);
        commit({ x: range, y: range });
    });
    sequence.addEventListener('pointerleave', () => { if (!drag) inspect(null); });
    sequence.addEventListener('keydown', event => {
        const target = event.target.closest('.pae-residue');
        if (!target) return;
        const i = Number(target.dataset.index);
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
            event.preventDefault();
            const next = Math.max(0, Math.min(n - 1, i + (event.key === 'ArrowRight' ? 1 : -1)));
            buttons[i].tabIndex = -1;
            buttons[next].tabIndex = 0;
            buttons[next].focus();
            inspect({ x: next, y: next });
        }
    });
    sequence.addEventListener('click', event => {
        // Pointer selection is handled by the drag gesture; native keyboard clicks have detail=0.
        const target = event.target.closest('.pae-residue');
        if (!target || event.detail !== 0) return;
        const i = Number(target.dataset.index);
        commit({ x: [i, i], y: [i, i] });
    });
    function cancelDrag() {
        if (!drag) return;
        const source = drag.source === 'plot' ? canvas : sequence;
        const pointer = drag.pointer;
        drag = null;
        if (source.hasPointerCapture(pointer)) source.releasePointerCapture(pointer);
        hover = null;
        paintOverlay();
        paintSequence();
        paintHover();
        highlight(null);
    }
    canvas.addEventListener('pointercancel', cancelDrag);
    sequence.addEventListener('pointercancel', cancelDrag);
    canvas.addEventListener('lostpointercapture', cancelDrag);
    sequence.addEventListener('lostpointercapture', cancelDrag);
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') { cancelDrag(); commit(null, false); highlight(null); }
    });
    $('pae-clear').addEventListener('click', () => { cancelDrag(); commit(null, false); highlight(null); });
    $('pae-reset').addEventListener('click', () => {
        if (ready) viewer.visual.reset({ camera: true }).catch(error => console.error('PAE camera reset failed', error));
    });
    $('pae-export').addEventListener('click', () => {
        // Export axes, the color legend and the current box as well as the matrix.
        const exported = document.createElement('canvas');
        const size = Math.max(600, Math.min(rasterSize, 1400));
        exported.width = size + 100;
        exported.height = size + 160;
        const ctx = exported.getContext('2d');
        ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, exported.width, exported.height);
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(canvas, 65, 35, size, size);
        ctx.fillStyle = '#222'; ctx.font = '13px sans-serif';
        ctx.fillText(document.title, 65, 20);
        ticks.forEach(i => {
            const p = (i + .5) / n * size;
            ctx.fillText(String(i + 1), 60 + p, size + 54);
            ctx.fillText(String(i + 1), 30, 39 + p);
        });
        ctx.textAlign = 'center';
        ctx.fillText('Scored token position', 65 + size / 2, size + 76);
        ctx.save(); ctx.translate(16, 35 + size / 2); ctx.rotate(-Math.PI / 2);
        ctx.fillText('Aligned token position (reference)', 0, 0); ctx.restore();
        const gradient = ctx.createLinearGradient(65, 0, size + 65, 0);
        palette.forEach((rgb, i) => gradient.addColorStop(i / 4, `rgb(${rgb.join(',')})`));
        ctx.fillStyle = gradient; ctx.fillRect(65, size + 94, size, 12);
        ctx.fillStyle = '#222';
        ctx.fillText(`Expected position error: 0 – ${data.maximum} Å`, 65 + size / 2, size + 128);
        if (selection) {
            ctx.strokeStyle = colors.both; ctx.lineWidth = 2;
            ctx.strokeRect(65 + selection.x[0] / n * size, 35 + selection.y[0] / n * size,
                (selection.x[1] - selection.x[0] + 1) / n * size, (selection.y[1] - selection.y[0] + 1) / n * size);
        }
        exported.toBlob(blob => {
            if (!blob) return;
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url; link.download = `${document.title.replace(/^PAE \| /, '')}-pae.png`;
            link.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        });
    });

    function structureIndex(event) {
        const r = event.eventData;
        if (!mapped || !r) return null;
        const atomNames = Array.isArray(r.atom_id) ? r.atom_id : r.atom_id ? [r.atom_id] : [];
        function candidates(atoms) {
            const found = new Set();
            atoms.forEach(atom => {
                const keys = [selectionKey(r.label_asym_id, 'label', r.seq_id, '', atom),
                    selectionKey(r.label_asym_id, 'auth', r.auth_seq_id, r.ins_code, atom)];
                keys.forEach(key => indexBySelection.get(key)?.forEach(i => found.add(i)));
            });
            return found;
        }
        // Atom-specific mappings take priority over whole-residue mappings.
        const atomic = candidates(atomNames);
        if (atomic.size) return atomic.size === 1 ? [...atomic][0] : null;
        const polymer = candidates(['']);
        return polymer.size === 1 ? [...polymer][0] : null;
    }
    host.addEventListener('PDB.molstar.mouseover', event => {
        const i = structureIndex(event);
        if (i !== null && !drag) inspect({ x: i, y: i }, false);
    });
    host.addEventListener('PDB.molstar.mouseout', () => { if (!drag) inspect(null, false); });
    host.addEventListener('PDB.molstar.click', event => {
        const i = structureIndex(event);
        if (i === null) return;
        commit({ x: [i, i], y: [i, i] }, false);
        buttons[i].scrollIntoView({ block: 'nearest', inline: 'nearest' });
    });
    paintOverlay();
    function structureError(error) {
        ready = false;
        $('pae-reset').disabled = true;
        console.error('Could not load PAE structure', error);
        $('pae-structure-status').textContent = 'Structure unavailable';
        host.textContent = 'Unable to load the structure. The PAE plot remains available.';
        warning('Structure loading failed. Check that this model has a readable CIF or PDB file.');
    }
    try {
        viewer = new PDBeMolstarPlugin();
        const syncTheme = MineProtMolstarTheme.register(viewer);
        viewer.render(host, {
            customData: { url: data.structure_url, format: 'cif', binary: false },
            alphafoldView: true, landscape: true, reactive: false,
            hideControls: true, sequencePanel: false, pdbeLink: false,
            hideCanvasControls: [], bgColor: MineProtMolstarTheme.backgroundColor(),
            granularity: 'element', selectInteraction: false,
        }).then(async () => {
            await viewer.visual.visibility({ polymer: true, het: true, carbs: true, nonStandard: true });
            ready = true;
            syncTheme();
            $('pae-structure-status').textContent = mapped ? 'pLDDT coloring · hover or click a residue / atom' : 'pLDDT coloring · linking unavailable';
            $('pae-reset').disabled = false;
            if (selection) updateViewer(false);
        }).catch(structureError);
    } catch (error) { structureError(error); }
})();
