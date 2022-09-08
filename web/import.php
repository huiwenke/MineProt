<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>import</title>
    <link rel="shortcut icon" type="image/png" href="/assets/img/logo.png">
    <link rel="stylesheet" type="text/css" href="/assets/css/style.css">
    <link rel="stylesheet" type="text/css" href="/assets/css/github-dark.min.css">
    <script src="/assets/js/highlight.min.js"></script>
    <script>
        hljs.highlightAll();
    </script>
</head>

<body>
    <?php
    include "header.html";
    ?>
    <main style="min-height: 100vh;">
        <?php
        include "form.php";
        ?>
        <section class="main">
            <div style="display: block; width: 100%;">
                <h1 style="margin-bottom: 8px; color:#efefef;">Generate command for importing</h1>
                <HR color=#21262d SIZE=1.5>
                <div class="card-inner-div">
                    <div style="color:#c9d1d9; margin-left: 16px; width: 100%;">
                        <div style="display: flex;">
                            <div style="width: 33.3%;">
                                <strong>System</strong>
                            </div>
                            <div>
                                <select id="system" onchange="selectSystem()">
                                    <option value="colabfold">ColabFold</option>
                                    <option value="alphafold">AlphaFold</option>
                                </select>
                            </div>
                        </div>
                        <br>
                        <div style="display: flex;">
                            <div style="width: 33.3%;">
                                <strong>Repository</strong>
                            </div>
                            <div>
                                <select id="repo_name">
                                    <?php
                                    foreach ($DATA_REPOS as $Data_Repo) {
                                        echo '<option value="' . $Data_Repo . '">' . $Data_Repo . '</option>';
                                    }
                                    ?>
                                    <option value="CREATE_NEW_REPO">Create new repository</option>
                                </select>
                            </div>
                        </div>
                        <br>
                        <div style="display: flex;">
                            <div style="width: 33.3%;">
                                <strong>Naming mode</strong>
                            </div>
                            <div>
                                <select id="name_mode">
                                    <option value="0">0: Use prefix</option>
                                    <option value="1">1: Use name in .a3m</option>
                                    <option value="2">2: Auto rename</option>
                                    <option value="3">3: Customize name</option>
                                </select>
                            </div>
                        </div>
                        <br>
                        <div style="display: flex;">
                            <div style="width: 33.3%;">
                                <strong>Path to data</strong>
                            </div>
                            <div style="width: 50%;">
                                <input class="input-import" id="data_path" placeholder="/path/to/your/data/for/importing" required="">
                            </div>
                        </div>
                        <br>
                        <div style="display: flex;">
                            <div style="width: 33.3%;">
                                <strong>Path to python3</strong>
                            </div>
                            <div style="width: 50%;">
                                <input class="input-import" id="python_path" placeholder="/path/to/your/python3" value="/usr/bin/python3">
                            </div>
                        </div>
                        <br>
                        <div style="display: flex;">
                            <div style="width: 33.3%;">
                                <strong>Path to MineProt scripts</strong>
                            </div>
                            <div style="width: 50%;">
                                <input class="input-import" id="script_path" placeholder="/path/to/your/MineProt/scripts" value=".">
                            </div>
                        </div>
                        <br>
                        <div id="colabfold_opt" name="system_opt" style="margin-top: 7px; display: flex;">
                            <div style="width: 33.3%;">
                                <strong>Parameters</strong>
                            </div>
                            <div>
                                <input type="checkbox" name="colabfold_args" value="--zip" />--zip
                                <input type="checkbox" name="colabfold_args" value="--relax" />--amber
                            </div>
                        </div>
                        <div id="alphafold_opt" name="system_opt" style="margin-top: 7px; display: none;">
                            Waiting...
                        </div>
                        <br>
                        <button class="btn" onclick="generateCode()"><strong>Generate</strong></button>
                    </div>
                </div>
                <pre style="font-size: 16px; font-weight: 500;"><code class="language-bash" id="code_for_import">#Code for import</code></pre>
            </div>
        </section>
    </main>
    <script>
        function selectSystem() {
            var currentSystem = document.getElementById("system");
            var Systems = document.getElementsByName("system_opt");
            for (i = 0; i < Systems.length; i++) {
                if (Systems[i].id == currentSystem.value + "_opt") {
                    Systems[i].style.display = "flex";
                } else Systems[i].style.display = "none";
            }
        }

        function generateCode() {
            var currentSystem = document.getElementById("system");
            var codeForImport = document.getElementById("code_for_import");
            codeForImport.innerHTML = "";
            var dataPath = document.getElementById("data_path").value;
            if (dataPath == "") {
                codeForImport.innerHTML = "# Where is your data for importing?";
                return;
            }
            var repoName = document.getElementById("repo_name").value;
            if (repoName == "CREATE_NEW_REPO") {
                codeForImport.innerHTML = "# Don't forget to replace CREATE_NEW_REPO with your new repo name.\n"
            }
            var scriptPath = document.getElementById("script_path").value;
            if (scriptPath != '') {
                codeForImport.innerHTML += "cd " + scriptPath + " \n";
            }
            codeForImport.innerHTML += currentSystem.value + "/import.sh " + dataPath + " --repo " + repoName + " \\\n";
            var nameMode = document.getElementById("name_mode").value;
            codeForImport.innerHTML += "--name-mode " + nameMode + " \\\n";
            var systemArgs = document.getElementsByName(currentSystem.value + "_args");
            for (i = 0; i < systemArgs.length; i++) {
                if (systemArgs[i].checked) {
                    codeForImport.innerHTML += systemArgs[i].value + " \\\n";
                }
            }
            var pythonPath = document.getElementById("python_path").value;
            if (pythonPath != '') {
                codeForImport.innerHTML += "--python " + pythonPath + " \\\n";
            }
            var apiURL = window.location.href.replace(window.location.pathname, "");
            codeForImport.innerHTML += "--url " + apiURL;
        }
    </script>
</body>

</html>