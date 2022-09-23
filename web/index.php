<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MineProt</title>
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
        if (count($DATA_REPOS) == 0) {
            include "no_repo.html";
        } else {
            include "welcome.html";
        }
        ?>
    </main>
</body>

</html>