// ==UserScript==
// @name         MineProt Sequenceserver Plugin
// @namespace    https://github.com/huiwenke/MineProt
// @version      0.1
// @description  link sequenceserver hits to MineProt search interface
// @author       Yunchi Zhu
// @include      <Please fill in your Sequenceserver URL here>
// ==/UserScript==

(function () {
    // Please fill in your MineProt URL here.
    MainFunction("", 0);
})();

function AddSearch(obj, MineProt_URL) {
    var data_hit_def = obj.parentNode.parentNode.attributes[2].value;
    var search_url = MineProt_URL + "/search.php?search=" + encodeURIComponent(data_hit_def);
    var spanNode = document.createElement('span');
    spanNode.className = "line";
    spanNode.innerHTML = "|";
    obj.appendChild(spanNode);
    var aNode = document.createElement('a');
    aNode.href = search_url;
    aNode.target = " _blank";
    var iNode = document.createElement('i');
    iNode.className = "fa fa-search";
    aNode.appendChild(iNode);
    var spanNode2 = document.createElement('span');
    spanNode2.innerHTML = " search";
    aNode.appendChild(spanNode2);
    obj.appendChild(aNode);
}

function MainFunction(MineProt_URL, hit_link_num) {
    var overview = document.getElementsByClassName("overview");
    if (overview.length < 1) {
        setTimeout(() => {
            MainFunction(MineProt_URL, hit_link_num)
        }, 500);
    }
    var hit_links = document.querySelectorAll("div[class='hit-links']");
    if (hit_links.length == 0 || hit_links.length > hit_link_num) {
        hit_link_num = hit_links.length;
        setTimeout(() => {
            MainFunction(MineProt_URL, hit_link_num)
        }, 500);
    }
    else {
        for (var i = 0; i < hit_links.length; i++) {
            AddSearch(hit_links[i], MineProt_URL);
        }
    }
}