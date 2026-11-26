// ==UserScript==
// @name         Foldseek to MineProt Plugin
// @namespace    https://github.com/huiwenke/MineProt
// @version      0.2
// @description  Link Foldseek hits to MineProt and realign structures with Salign.
// @author       Yunchi Zhu
// @include      <Please fill in your Foldseek APP URL here>
// ==/UserScript==

(function () {
    // Please fill in your MineProt URL here.
    MainFunction("please://fill.your.mineprot.url/here", 0);
})();

function mineprotHit(aNode) {
    const table = aNode.closest('table.result-table');
    const heading = table && table.parentNode.querySelector('.flex.d-flex h2 span');
    const name = aNode.title.trim().replace(/\.(?:pdb|cif|mmcif)(?:\.gz)?$|\.fcz$/i, '');
    if (!heading || !name || !heading.textContent.trim()) return null;
    return { name, repo: heading.textContent.trim() };
}

function AddSearch(aNode, MineProt_URL) {
    const hit = mineprotHit(aNode);
    if (!hit) return;
    const params = new URLSearchParams({ search: hit.name, 'repo[]': hit.repo });
    const url = MineProt_URL.replace(/\/+$/, '') + '/search.php?' + params;
    if (aNode.href !== url) aNode.href = url;
    AddRealign(aNode, MineProt_URL);
}

function foldseekQueryURL(location) {
    // Preserve deployments below a path prefix as well as hash-based routing.
    const route = location.hash.startsWith('#/') ? location.hash.slice(1) : location.pathname;
    const match = route.match(/^(.*?)\/result\/([^/]+)\/\d+(?:\/|$|\?)/);
    if (!match) throw new Error('Open a Foldseek result page before realigning.');
    const prefix = location.hash.startsWith('#/')
        ? location.pathname.replace(/\/?(?:index\.html)?$/, '/')
        : match[1] + '/';
    return new URL(prefix + 'api/result/' + match[2] + '/query', location.href).href;
}

async function foldseekQueryStructure(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Could not download the query structure (HTTP ${response.status}).`);
    const structure = await response.text();
    if (!/^(?:ATOM  |HETATM)/m.test(structure) && !/^\s*_atom_site\./m.test(structure)) {
        throw new Error('Foldseek returned no PDB/CIF coordinates for this query.');
    }
    return structure;
}

function mineprotSalignForm(doc, MineProt_URL, hit, structure, hinge) {
    const form = doc.createElement('form');
    form.method = 'POST';
    form.action = MineProt_URL.replace(/\/+$/, '') + '/api/salign/index.php';
    for (const [name, value] of Object.entries({
        structure, search: hit.name, 'repo[]': hit.repo, tmscore: '0', hinge
    })) {
        const input = doc.createElement('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        form.appendChild(input);
    }
    return form;
}

function AddRealign(aNode, MineProt_URL) {
    const cell = aNode.closest('tr').querySelector('td.alignment-action');
    if (!cell || cell.querySelector('.mineprot-realign')) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'mineprot-realign v-btn v-btn--icon v-btn--round v-btn--text v-size--default';
    button.title = 'Realign query and target in MineProt Salign';
    button.setAttribute('aria-label', button.title);
    // Inline realign.svg so the icon works without an external image request.
    button.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2130 1776"
        width="24" height="24" aria-hidden="true" focusable="false">
        <g transform="translate(-1179 -350)" fill="#727272" fill-rule="evenodd">
            <path d="M3305.36 1767.58 3127.97 1944.97 2773.62 1590.62 2951.02 1413.23Z"/>
            <path d="M1712.75 1591.86 1356.72 1947.89 1179.33 1770.5 1535.36 1414.47Z"/>
            <path d="M1714.86 886.64 1537.47 1064.03 1181.01 707.569 1358.4 530.179Z"/>
            <path d="M2953.37 1415.59 2775.98 1592.98 2598.58 1415.59 2775.98 1238.2Z"/>
            <path d="M2775.97 1592.98 2598.58 1770.37 1711.77 883.548 1889.16 706.158Z"/>
            <path d="M2598.58 1770.37 2421.19 1947.76 2243.8 1770.37 2421.19 1592.98Z"/>
            <path d="M2598.58 1415.59 2421.19 1592.98 2243.8 1415.59 2421.19 1238.2Z"/>
            <path d="M2421.2 1238.2 2243.8 1415.59 2066.41 1238.2 2243.8 1060.81Z"/>
            <path d="M2243.8 1415.59 2066.41 1592.98 1889.02 1415.59 2066.41 1238.2Z"/>
            <path d="M2598.45 1060.68 2421.06 1238.07 2243.67 1060.68 2421.06 883.286Z"/>
            <path d="M3127.97 1944.97 2950.58 2122.36 1358.53 530.31 1535.92 352.92Z"/>
            <path d="M2066.42 883.416 1889.02 1060.81 1711.63 883.416 1889.02 706.026Z"/>
            <path d="M1889.03 1060.81 1711.64 1238.2 1534.25 1060.81 1711.64 883.416Z"/>
            <path d="M2243.94 706.156 2066.55 883.546 1889.16 706.156 2066.55 528.766Z"/>
            <path d="M3130.76 1238.19 2243.81 2125.15 2066.42 1947.76 2953.37 1060.8Z"/>
            <path d="M2243.81 1770.37 2066.42 1947.76 1889.02 1770.37 2066.42 1592.98Z"/>
            <path d="M2066.42 1592.98 1889.02 1770.37 1711.63 1592.98 1889.02 1415.59Z"/>
            <path d="M1889.03 1415.59 1711.64 1592.98 1534.25 1415.59 1711.64 1238.2Z"/>
            <path d="M1711.64 1238.2 1534.24 1415.59 1356.85 1238.2 1534.24 1060.81Z"/>
            <path d="M3130.76 1238.2 2953.37 1415.59 2775.98 1238.2 2953.37 1060.81Z"/>
            <path d="M2953.37 1060.81 2775.98 1238.2 2598.59 1060.81 2775.98 883.416Z"/>
            <path d="M3131.05 528.346 1534.11 2125.28 1356.72 1947.89 2953.66 350.956Z"/>
            <path d="M2598.59 706.026 2421.2 883.416 2243.81 706.026 2421.2 528.636Z"/>
            <path d="M2421.2 528.636 1534.24 1415.59 1356.85 1238.2 2243.81 351.246Z"/>
            <path d="M3308.44 705.735 2951.32 1062.85 2773.93 885.457 3131.05 528.345Z"/>
        </g>
    </svg>`;
    button.addEventListener('click', async event => {
        event.preventDefault();
        event.stopPropagation();
        let hinge = window.prompt('Salign hinge (integer 0–9):\nUsed for single-chain pairs; ignored for complexes.', '0');
        if (hinge === null) return;
        hinge = hinge.trim();
        if (!/^[0-9]$/.test(hinge)) {
            alert('Hinge must be an integer from 0 to 9.');
            return;
        }
        let resultWindow;
        button.disabled = true;
        try {
            const hit = mineprotHit(aNode);
            if (!hit) throw new Error('Could not determine the target ID and repository.');
            const queryURL = foldseekQueryURL(window.location);
            // Reserve the tab during the click, before fetching, to avoid popup blocking.
            resultWindow = window.open('', '_blank');
            if (!resultWindow) throw new Error('Allow popups to open the Salign result.');
            resultWindow.opener = null;
            resultWindow.document.title = 'MineProt Salign';
            resultWindow.document.body.textContent = 'Loading query structure…';
            const structure = await foldseekQueryStructure(queryURL);
            if (resultWindow.closed) return;
            // A navigation form supports cross-origin POST and the result redirect without CORS.
            const form = mineprotSalignForm(resultWindow.document, MineProt_URL, hit, structure, hinge);
            resultWindow.document.body.appendChild(form);
            form.submit();
        } catch (error) {
            if (resultWindow && !resultWindow.closed) resultWindow.close();
            alert(`MineProt Salign: ${error.message || error}`);
        } finally {
            button.disabled = false;
        }
    });
    cell.appendChild(button);
}

function MainFunction(MineProt_URL, hit_link_num) {
    // Keep the startup signature compatible with existing embedded installations.
    if (!document.body) {
        setTimeout(() => MainFunction(MineProt_URL, hit_link_num), 500);
        return;
    }
    const update = () => {
        document.querySelectorAll('table.result-table td[data-label="Target"] a[rel="noopener"][title]')
            .forEach(link => AddSearch(link, MineProt_URL));
    };
    update();
    // Foldseek replaces table rows on paging, sorting, query and database changes.
    if (MainFunction.observer) MainFunction.observer.disconnect();
    let pending = false;
    MainFunction.observer = new MutationObserver(() => {
        if (pending) return;
        pending = true;
        setTimeout(() => {
            pending = false;
            update();
        }, 0);
    });
    MainFunction.observer.observe(document.body, { childList: true, subtree: true });
}
