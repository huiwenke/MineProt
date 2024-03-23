// ==UserScript==
// @name         MineProt to Foldseek Plugin
// @namespace    https://github.com/huiwenke/MineProt
// @version      0.2
// @description  Generate buttons for directly sending pdb files from MineProt search interface to Foldseek.
// @author       Yunchi Zhu
// @include      <Please fill in your MineProt URL here>
// ==/UserScript==

(function () {
    // You can replace the URL with your local Foldseek webapp.
    MineProt2Foldseek("https://search.foldseek.com");
})();

function MineProt2Foldseek(FoldseekURL) {
    var overview = document.getElementsByClassName("aside_right");
    if (overview.length < 1) {
        setTimeout(() => {
            MineProt2Foldseek(FoldseekURL)
        }, 500);
        return;
    }
    else {
        var searchResultLinks = document.getElementsByName("search_result_link");
        for (var i = 0; i < searchResultLinks.length; i++) {
            AddSeek(searchResultLinks[i], FoldseekURL);
        }
    }
}

function AddSeek(obj, FoldseekURL) {
    var buttonNode = document.createElement('button');
    buttonNode.className = "btn";
    buttonNode.style = "background-color: #fff; color: #1e1e1e;";
    buttonNode.onclick = function () {
        var fileURL = window.location.protocol + "//" + window.location.host + obj.id + ".pdb";
        urlToFileObject(fileURL, function (file) {
            const fd = new FormData();

            fd.append("q", file);
            fd.append("mode", "3diaa");
            fd.append("database[]", "afdb50");
            fd.append("database[]", "afdb-swissprot");
            fd.append("database[]", "afdb-proteome");
            fd.append("database[]", "cath50");
            fd.append("database[]", "mgnify_esm30");
            fd.append("database[]", "pdb100");
            fd.append("database[]", "gmgcl_id");

            var resultOK = false;

            fetch(FoldseekURL + "/api/ticket", {
                'Accept': 'application/json',
                'method': "POST",
                'body': fd
            }).then(r => {
                resultOK = r.ok;
                return r.json()
            }).then(r => {
                if (resultOK) {
                    window.location = FoldseekURL + `/result/${r.id}/0`;
                }
                else if (typeof (r.error) === "string") {
                    alert(r.error);
                }
                else {
                    throw "Failed to upload file";
                }
            }).catch(e => {
                alert(e);
            });
        });
    }
    buttonNode.innerHTML = "<strong>Foldseek</strong>";
    obj.appendChild(buttonNode);
}

function urlToFileObject(url, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.responseType = 'arraybuffer';
    xhr.onload = function () {
        if (this.status == 200) {
            var blob = new Blob([this.response], { type: 'application/octet-stream' });
            var filename = url.split('/').pop()
            var file = new File([blob], filename);
            callback(file);
        }
    };
    xhr.send();
}