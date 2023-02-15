// ==UserScript==
// @name         MineProt AlphaFill Plugin
// @namespace    https://github.com/huiwenke/MineProt
// @version      0.1
// @description  Generate buttons for directly sending cif files from MineProt search interface to AlphaFill.
// @author       Yunchi Zhu
// @include      <Please fill in your MineProt URL here>
// ==/UserScript==

(function () {
    // You can replace the URL with your local AlphaFill webapp.
    MineProt2AlphaFill("https://alphafill.eu");
})();

function MineProt2AlphaFill(AlphaFillURL) {
    var overview = document.getElementsByClassName("aside_right");
    if (overview.length < 1) {
        setTimeout(() => {
            MineProt2AlphaFill(AlphaFillURL)
        }, 500);
        return;
    }
    else {
        var searchResultLinks = document.getElementsByName("search_result_link");
        for (var i = 0; i < searchResultLinks.length; i++) {
            AddFill(searchResultLinks[i], AlphaFillURL);
        }
    }
}

function AddFill(obj, AlphaFillURL) {
    var buttonNode = document.createElement('button');
    buttonNode.className = "btn";
    buttonNode.style = "background-color: #ff9933; color: #3366cc;";
    buttonNode.onclick = function () {
        var fileURL = window.location.protocol + "//" + window.location.host + obj.id;
        urlToFileObject(fileURL, function (file) {
            const fd = new FormData();

            fd.append("structure", file);

            var resultOK = false;

            fetch(AlphaFillURL + "/v1/aff", {
                'Accept': 'application/json',
                'method': "POST",
                'body': fd
            }).then(r => {
                resultOK = r.ok;
                return r.json()
            }).then(r => {
                if (resultOK) {
                    window.location = AlphaFillURL + `/model?id=${r.id}`;
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
    buttonNode.innerHTML = "<strong>αfill</strong>";
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