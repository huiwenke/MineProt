<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Search | <?php echo $_GET["search"]; ?></title>
    <link rel="shortcut icon" type="image/png" href="./assets/img/logo.png">
    <link rel="stylesheet" type="text/css" href="./assets/css/style.css">
    <link rel="stylesheet" type="text/css" href="./assets/css/pdbe-molstar-1.2.1.css">
    <script type="text/javascript" src="./assets/js/pdbe-molstar-plugin-1.2.1.js"></script>
</head>

<body>
    <?php
    include "header.html";
    ?>
    <main style="min-height: 100vh;">
        <?php
        include "form.php";
        if (array_key_exists("repo", $_GET)) {
            $Search_Repos = implode(',', $_GET["repo"]);
        } else $Search_Repos = implode(',', $DATA_REPOS);
        $Search_Results_Json = search_api($Search_Repos, $_GET["search"]);
        $Search_Results = json_decode($Search_Results_Json, true);
        ?>
        <section class="main">
            <div style="display: block; width: 100%;">
                <h2 class="main_h2">
                    <?php
                    $Search_Result_Num = count($Search_Results);
                    if ($Search_Result_Num == 0) {
                        echo " No result";
                    } else if ($Search_Result_Num >= 100) {
                        echo " Top 100 results";
                    } else {
                        echo $Search_Result_Num . " results";
                    }
                    ?>
                </h2>
                <HR color=#21262d SIZE=1.5>
                <br>
                <?php
                if ($Search_Result_Num > 0) {
                    include "page.php";
                    $Page_Info = page_info($Search_Result_Num);
                    $Search_Results_Displayed = array_slice($Search_Results, $Page_Info["top"], $Page_Info["length"]);
                    foreach ($Search_Results_Displayed as $Search_Result) {
                        form_search_result($Search_Result);
                    }
                }
                ?>
            </div>
        </section>
        <?php
        if ($Search_Result_Num > 0) {
            include "legend.php";
        }
        ?>
    </main>
    <script>
        function MainFunction() {
            var isExpanded = document.getElementsByClassName("msp-layout-expanded");
            var header = document.getElementsByTagName("header")[0];
            if (isExpanded.length==0) {
                header.style.visibility = "visible";
            } else header.style.visibility = "hidden";
            setTimeout(() => {
                MainFunction()
            }, 100)
        }
        MainFunction();
    </script>
</body>

</html>