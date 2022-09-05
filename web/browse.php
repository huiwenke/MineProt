<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Browse</title>
    <link rel="shortcut icon" type="image/png" href="/assets/img/logo.png">
    <link rel="stylesheet" type="text/css" href="/assets/css/style.css">
</head>

<body>
    <?php
    include "header.php";
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
                    $Files = array_diff(scandir("/var/www/data/" . $_GET["repo"]), array('.', '..'));
                    echo "
                    <table>
                        <thead>
                            <tr align='left'>
                                <th>Name</th>
                                <th>Structure</th>
                                <th>pLDDT</th>
                                <th>Annotation</th>
                            </tr>
                        </thead>
                    ";
                    foreach ($Files as $File) {
                        echo "<tr>";
                        if (pathinfo($File)["extension"] == "json") {
                            form_td($_GET["repo"], $File);
                        }
                        echo "</tr>";
                    }
                    echo "</table>";
                }
                ?>
            </div>
        </section>
    </main>
</body>

</html>