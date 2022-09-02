<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?php echo $_GET["search"]; ?></title>
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
        if (array_key_exists("repo", $_GET)) {
            $Search_Repos = implode(',', $_GET["repo"]);
        } else $Search_Repos = implode(',', $Data_Repos);
        include "search_api.php";
        $Search_Results = search_api($Search_Repos, $_GET["search"]);
        ?>
        <section class="main">
            <div style="display: block; width: 100%;">
                <h2 class="main_h2">All activity</h2>
                <HR color=#21262d SIZE=1.5>
                <br>
                <div class="card-inner-div">
                    <div style="display: flex;">
                        <div style="margin-left: 16px;">
                            <strong style="color:#c9d1d9; margin-top: 7px;">MP0001</strong>
                            <div style="color:#c9d1d9; margin-top: 7px;">
                                Similar to <a class="card-link user-properties-link" href="#">WP_009801651.1</a>: Bone morphogenetic protein 2
                            </div>
                            <br>
                            <span style="color: #8b949e;">
                                <a href="#" style="margin-right:16px; color: inherit;" class="user-properties-link">x repositories</a>
                                <a href="#" style="margin-right:16px; color: inherit;" class="user-properties-link">y followers</a>
                            </span>
                        </div>
                    </div>
                </div>
                <br>
            </div>
        </section>
    </main>
</body>

</html>