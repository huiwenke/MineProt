<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MineProt</title>
    <link rel="shortcut icon" type="image/png" href="../assets/img/logo.png">
    <link rel="stylesheet" type="text/css" href="../assets/css/style.css">
</head>

<body>
    <?php
    include "header.html";
    include "../api.php";
    ?>
    <main style="min-height: 100vh;">
        <section class="main_salign">
            <div style="display: block; width: 100%;">
                <form action="../api/salign/index.php" method="post">
                    <br><br>
                    <label class="wrapper">
                        <textarea name="structure" class="form-control-header" style="height: 25vh;" placeholder="Paste query structure (PDB) here..." required=""></textarea>
                    </label>
                    <br>
                    <h2 class="h2_aside">Protein Repositories</h2>
                    <HR color=#21262d SIZE=1.5>
                    <?php
                    include "../display.php";
                    foreach ($DATA_REPOS as $Data_Repo) {
                        form_repo($Data_Repo);
                    }
                    ?>
                    <HR color=#21262d SIZE=1.5><br>
                    <div style="display: flex;">
                        <div style="width: 15%; color: white;">
                            <strong>Key words</strong>
                        </div>
                        <div style="width: 85%; color: white;">
                            <label class="wrapper">
                                <input name="search" class="form-control-header" placeholder="🔍︎ Enter keywords...">
                            </label>
                        </div>
                    </div>
                    <br>
                    <div style="display: flex;">
                        <div style="width: 15%; color: white;">
                            <strong>Max RMSD</strong>
                        </div>
                        <div style="width: 25%; color: white;">
                            <label class="wrapper">
                                <input name="rmsd" class="form-control-header" value=5>
                            </label>
                        </div>
                        <div style="width: 10%;">
                        </div>
                        <div style="width: 50%;">
                            <button class="btn" type="submit" style="width: 100%;"><strong>Search</strong></button>
                        </div>
                    </div>
                </form>
            </div>
        </section>
    </main>
</body>

</html>