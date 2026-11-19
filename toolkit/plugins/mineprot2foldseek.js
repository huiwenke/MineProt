// ==UserScript==
// @name         MineProt to Foldseek Plugin
// @namespace    https://github.com/huiwenke/MineProt
// @version      0.3
// @description  Send MineProt structures to Foldseek monomer or multimer search.
// @author       Yunchi Zhu
// @include      <Please fill in your MineProt URL here>
// ==/UserScript==

(function () {
    // You can replace the URL with your local Foldseek webapp.
    MineProt2Foldseek("https://search.foldseek.com");
})();

function MineProt2Foldseek(FoldseekURL) {
    if (document.getElementsByClassName("aside_right").length < 1) {
        setTimeout(() => MineProt2Foldseek(FoldseekURL), 500);
        return;
    }
    for (const link of document.getElementsByName("search_result_link")) {
        AddSeek(link, FoldseekURL.replace(/\/+$/, ""));
    }
}

function AddSeek(obj, FoldseekURL) {
    if (obj.querySelector(".mineprot-foldseek")) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn mineprot-foldseek";
    button.style = "background-color: #fff; color: #1e1e1e;";
    button.innerHTML = "<strong>Foldseek</strong>";
    button.title = "Search with Foldseek; automatically detect monomer or multimer";
    button.onclick = async function () {
        button.disabled = true;
        button.textContent = "Submitting…";
        try {
            // Use the template's encoded download URL (names may contain spaces or #).
            const pdbLink = obj.querySelector('a[href$=".pdb"]');
            if (!pdbLink) throw new Error("No PDB download link found.");
            const response = await fetch(pdbLink.href);
            if (!response.ok) throw new Error(`Failed to download PDB (HTTP ${response.status}).`);
            const pdb = await response.text();
            const multimer = foldseekProteinChainCount(pdb) > 1;
            button.textContent = multimer ? "Submitting multimer…" : "Submitting monomer…";
            const databases = await foldseekDatabases(FoldseekURL, multimer);
            const ticket = await submitFoldseek(FoldseekURL, pdb, multimer, databases);
            window.location.href = foldseekTicketURL(FoldseekURL, ticket);
        } catch (error) {
            alert(`Foldseek: ${error.message || error}`);
        } finally {
            button.disabled = false;
            button.innerHTML = "<strong>Foldseek</strong>";
        }
    };
    obj.appendChild(button);
}

function foldseekProteinChainCount(pdb) {
    const chains = new Set();
    // Count protein C-alpha chains, not DNA/RNA, water, or ligand chains.
    // Only inspect the first model: NMR ensembles are not multimers.
    const modifiedAminoAcids = new Set(["MSE", "SEC", "PYL", "SEP", "TPO", "PTR", "HYP", "CSO"]);
    for (const line of pdb.split(/\r?\n/)) {
        const record = line.slice(0, 6).trim();
        if (record === "ENDMDL" || record === "END") break;
        if (record !== "ATOM" && record !== "HETATM") continue;
        if (line.slice(12, 16).trim() !== "CA") continue;
        const element = line.slice(76, 78).trim();
        if (element && element !== "C") continue;
        if (record === "HETATM" && !modifiedAminoAcids.has(line.slice(17, 20).trim())) continue;
        chains.add(line.slice(21, 22));
    }
    if (chains.size === 0) {
        throw new Error("No protein C-alpha atoms found in the PDB structure.");
    }
    return chains.size;
}

async function foldseekDatabases(FoldseekURL, multimer) {
    const response = await fetch(FoldseekURL + "/api/databases/all", {
        headers: { Accept: "application/json" }
    });
    if (!response.ok) throw new Error(`Failed to load databases (HTTP ${response.status}).`);
    const data = await response.json();
    if (!Array.isArray(data.databases)) throw new Error("Invalid Foldseek database response.");
    // Match Databases.vue, including the defaults selected by each search form.
    const available = data.databases.filter(db =>
        db.status === "COMPLETE" && !db.interface && !db.motif && !db.rna &&
        (!multimer || db.complex)
    );
    const databases = available.filter(db => db.default).map(db => db.path);
    if (databases.length === 0) {
        throw new Error(`No ready default ${multimer ? "multimer" : "monomer"} databases available on this Foldseek server.`);
    }
    return databases;
}

async function submitFoldseek(FoldseekURL, pdb, multimer, databases) {
    // Both forms use /api/ticket; multimer search is selected by the mode prefix.
    // Send text as application/x-www-form-urlencoded, as the web forms do.
    const body = new URLSearchParams();
    body.append("q", pdb.endsWith("\n") ? pdb : pdb + "\n");
    body.append("mode", multimer ? "complex-3diaa" : "3diaa");
    body.append("email", "");
    for (const database of databases) body.append("database[]", database);
    const response = await fetch(FoldseekURL + "/api/ticket", {
        method: "POST",
        headers: { Accept: "application/json" },
        body
    });
    let ticket;
    try {
        ticket = await response.json();
    } catch (_) {
        throw new Error(`Invalid Foldseek submission response (HTTP ${response.status}).`);
    }
    if (!response.ok) {
        throw new Error(typeof ticket.error === "string" ? ticket.error : `Submission failed (HTTP ${response.status}).`);
    }
    return ticket;
}

function foldseekTicketURL(FoldseekURL, ticket) {
    switch (ticket.status) {
        case "PENDING":
        case "RUNNING":
        case "COMPLETE":
            if (typeof ticket.id !== "string" || !ticket.id) throw new Error("Foldseek returned no ticket ID.");
            return FoldseekURL + (ticket.status === "COMPLETE"
                ? `/result/${encodeURIComponent(ticket.id)}/0`
                : `/queue/${encodeURIComponent(ticket.id)}`);
        case "RATELIMIT":
            throw new Error("Rate limit reached. Please try again later.");
        case "MAINTENANCE":
            throw new Error("Foldseek is under maintenance. Please try again later.");
        default:
            throw new Error(typeof ticket.error === "string" ? ticket.error : `Submission failed (${ticket.status || "unknown status"}).`);
    }
}
