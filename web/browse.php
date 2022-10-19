<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Browse</title>
    <link rel="shortcut icon" type="image/png" href="./assets/img/logo.png">
    <link rel="stylesheet" type="text/css" href="./assets/css/style.css">
</head>

<body>
    <?php
    include "header.html";
    ?>
    <main style="min-height: 100vh;">
        <?php
        include "form.php";
        ?>
        <section class="main_browse">
            <div style="display: block; width: 100%;">
                <h1 style="margin-bottom: 8px; color:#efefef;">Browse <?php echo $_GET["repo"]; ?></h1>
                <HR color=#21262d SIZE=1.5>
                <?php
                if ($_GET["repo"] == '') {
                    foreach ($DATA_REPOS as $Data_Repo) {
                        echo "
                        <h3>
                            <li style='color: #efefef;'>
                                <a style='color: #efefef;' class='user-properties-link' href='browse.php?repo=$Data_Repo'>$Data_Repo</a>
                            </li>
                        </h3>
                        ";
                    }
                } else {
                    echo "
                    <form method='post' onsubmit='return reSubmit()'>
                        <button style='background-color: #0969da;' class='btn' name='sort' value='plddt'>⇅ Sort by pLDDT</button>
                        <button style='background-color: #0969da;' class='btn' name='sort' value=''>⇅ Sort by name</button>
                        <button style='background-color: #FF5733;' class='btn' title='Refresh cache' onclick=clearCache('" . $_GET["repo"] . "')>⟳ Refresh</button>
                    </form>
                    <br>";
                    $ob_File = sys_get_temp_dir() . "/MP_BROWSE_" . md5($_GET["repo"] . filemtime(getenv("MP_REPO_PATH") . $_GET["repo"])) . '_' . $_POST["sort"];
                    if (file_exists($ob_File)) {
                        include($ob_File);
                    } else {
                        ob_start();
                        $Files = array_diff(scandir(getenv("MP_REPO_PATH") . $_GET["repo"]), array('.', '..'));
                        echo "
                    <table>
                        <thead>
                            <tr align='left'>
                                <th>Name</th>
                                <th>Structure</th>
                                <th>pLDDT</th>
                                <th>MSA</th>
                                <th>Annotation</th>
                            </tr>
                        </thead>
                        <tbody>
                    ";
                        $Table = array();
                        foreach ($Files as $File) {
                            if (pathinfo($File)["extension"] == "json") {
                                array_push($Table, get_api_tr($_GET["repo"], $File));
                            }
                        }
                        if ($_POST["sort"] == "plddt") {
                            array_multisort(array_column($Table, "plddt"), SORT_DESC, $Table);
                        } else {
                            array_multisort(array_column($Table, "name"), $Table);
                        }
                        foreach ($Table as $Table_tr) {
                            form_td($Table_tr);
                        }
                        echo "</tbody></table>";
                        $f_ob_File = fopen($ob_File, 'w');
                        fwrite($f_ob_File, ob_get_contents());
                        fclose($f_ob_File);
                        ob_end_flush();
                    }
                }
                ?>
            </div>
        </section>
    </main>
    <script>
        var ifReSubmit = true;

        function clearCache(repoName) {
            var httpRequest = new XMLHttpRequest();
            httpRequest.open("GET", "./api/cache/clear.php?repo=" + repoName, true);
            httpRequest.send();
            ifReSubmit = false;
            location.reload()
        }

        function reSubmit() {
            return ifReSubmit;
        }
    </script>
</body>

</html>