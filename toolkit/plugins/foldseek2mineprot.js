// ==UserScript==
// @name         Foldseek to MineProt Plugin
// @namespace    https://github.com/huiwenke/MineProt
// @version      0.1
// @description  Link Foldseek hits to MineProt search interface.
// @author       Yunchi Zhu
// @include      <Please fill in your Foldseek APP URL here>
// ==/UserScript==

(function () {
    // Please fill in your MineProt URL here.
    MainFunction("please://fill.your.mineprot.url/here", 0);
})();

function AddSearch(aNode, MineProt_URL) {
    var protName = aNode.title;
    const extensions = ['.pdb', '.cif', '.pdb.gz', '.cif.gz', '.fcz'];
    for (let ext of extensions) {
        if (protName.toLowerCase().endsWith(ext)) {
            protName = protName.slice(0, -ext.length);
        }
    }
    var repoName = aNode.parentNode.parentNode.parentNode.parentNode.parentNode.querySelector('.flex.d-flex h2 span').textContent;
    var search_url = MineProt_URL + "/search.php?search=" + encodeURIComponent(protName) + "&repo[]=" + repoName;
    aNode.href = search_url;
}

function MainFunction(MineProt_URL, hit_link_num) {
    var overview = document.getElementsByClassName("v-table result-table");
    if (overview.length < 1) {
        setTimeout(() => {
            MainFunction(MineProt_URL, hit_link_num)
        }, 500);
        return;
    }
    var hit_links = document.querySelectorAll("a[rel='noopener']");
    if (hit_links.length == 0 || hit_links.length > hit_link_num) {
        hit_link_num = hit_links.length;
        setTimeout(() => {
            MainFunction(MineProt_URL, hit_link_num)
        }, 500);
        var buttons = document.querySelectorAll('div.v-btn, div.v-tab, button.v-btn');
        buttons.forEach(function (button) {
            button.addEventListener('click', function (event) {
                MainFunction(MineProt_URL, 0);
            });
        });
        return;
    }
    else {
        for (var i = 0; i < hit_links.length; i++) {
            AddSearch(hit_links[i], MineProt_URL);
        }
    }
}
