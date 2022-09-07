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
                <h1 style="margin-bottom: 8px; color:#efefef;">Use MineProt scripts to import</h1>
                <HR color=#21262d SIZE=1.5>
                <?php echo code_prepare_scripts(); ?>
                <h3 style="margin-bottom: 8px; color:#efefef;">Generate code for import</h3>
                <div class="card-inner-div">
                    <form method="post">
                        <div style="color:#c9d1d9; margin-left: 16px; width=100%;">
                            <div>
                                <strong>System</strong>
                                <select style="margin-left: 60px;" id="system" name="system" onchange="selectSystem()">
                                    <option value="colabfold">ColabFold</option>
                                    <option value="alphafold">AlphaFold</option>
                                </select>
                            </div>
                            <br>
                            <div>
                                <strong>Path</strong>
                                <input style="margin-left: 84px;" name="data_path" placeholder="/path/to/your/results" required="">
                            </div>
                            <br>
                            <div id="colabfold_opt" name="system_opt" style="margin-top: 7px;">
                                <strong>Parameters</strong>
                                <input style="margin-left: 32px;" type="checkbox" name="--zip" value="--zip" />--zip
                                <input type="checkbox" name="--amber" value="--amber" />--amber
                            </div>
                            <div id="alphafold_opt" name="system_opt" style="margin-top: 7px; display: none;">
                                Waiting...
                            </div>
                            <br>
                            <button class="btn" type="submit"><strong>Generate</strong></button>
                        </div>
                    </form>
                </div>
                <?php echo generate_code(); ?>
            </div>
        </section>
    </main>
    <script>
        function selectSystem() {
            var currentSystem = document.getElementById("system");
            var Systems = document.getElementsByName("system_opt");
            for (i = 0; i < Systems.length; i++) {
                if (Systems[i].id == currentSystem.value + "_opt") {
                    Systems[i].style.display = "";
                } else Systems[i].style.display = "none";
            }
        }
    </script>
</body>

</html>