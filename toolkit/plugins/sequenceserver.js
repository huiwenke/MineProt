// ==UserScript==
// @name         MineProt Sequenceserver TamperMonkey Plugin
// @namespace    https://github.com/huiwenke/MineProt
// @version      0.2
// @description  link sequenceserver hits to MineProt search interface. Please install this script in TamperMonkey plugin (you can get it from https://www.tampermonkey.net/ or your browser's plugin store)
// @author       Yunchi Zhu
// @include      <Please fill in your Sequenceserver URL here>
// ==/UserScript==

(function () {
    // Please fill in your MineProt URL here.
    MainFunction("please://fill.your.mineprot.url/here", 0);
})();

function AddSearch(obj, MineProt_URL) {
    var data_hit_def = obj.parentNode.parentNode.attributes[2].value;
    var search_url = MineProt_URL + "/search.php?search=" + encodeURIComponent(data_hit_def);
    if (search_url.includes("%7Crepo%3D")) {
        search_url = search_url.replace("%7Crepo%3D", "&repo[]=");
    }
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
        return;
    }
    var hit_links = document.querySelectorAll("div[class='hit-links']");
    if (hit_links.length == 0 || hit_links.length > hit_link_num) {
        hit_link_num = hit_links.length;
        setTimeout(() => {
            MainFunction(MineProt_URL, hit_link_num)
        }, 500);
        return;
    }
    else {
        for (var i = 0; i < hit_links.length; i++) {
            AddSearch(hit_links[i], MineProt_URL);
        }
    }
}