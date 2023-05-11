<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MineProt</title>
    <link rel="shortcut icon" type="image/png" href="../assets/img/logo.png">
    <link rel="stylesheet" type="text/css" href="../assets/css/style.css">
    <link rel="stylesheet" type="text/css" href="../assets/css/pdbe-molstar-1.2.1.css">
    <script type="text/javascript" src="../assets/js/pdbe-molstar-plugin-1.2.1.js"></script>
</head>

<body>
    <?php
    include "header.html";
    ?>
    <main style="min-height: 100vh;">
        <?php
        $TMP_DIR = sys_get_temp_dir() . "/MP_SALIGN_" . $_GET["rid"];
        if (!file_exists("$TMP_DIR/result.tar.gz")) {
            include "wait.php";
            header("refresh: 5");
            exit;
        }
        if (is_numeric($_GET["rmsd"])) {
            $Max_RMSD = (float)$_GET["rmsd"];
        } else $Max_RMSD = PHP_INT_MAX;
        $Salign_Results = array();
        $Lines = file("$TMP_DIR/query.out");
        foreach ($Lines as $Line) {
            if ($Line[0] == '#') continue;
            $Items = explode("\t", $Line);
            if ((float)$Items[4] > $Max_RMSD) continue;
            $Items[1] = substr($Items[1], 0, -2);
            $Salign_Result = array(
                "PDB1" => "MP_SALIGN_" . $_GET["rid"] . "/query_" . pathinfo($Items[1])["filename"],
                "PDB2" => $Items[1],
                "TM1" => (float)$Items[2],
                "TM2" => (float)$Items[3],
                "RMSD" => (float)$Items[4],
                "ID1" => (float)$Items[5],
                "ID2" => (float)$Items[6],
                "IDali" => (float)$Items[7],
                "L1" => (int)$Items[8],
                "L2" => (int)$Items[9],
                "Lali" => (int)$Items[10],
                "TOTAL" => "MP_SALIGN_" . $_GET["rid"] . "/result.tar.gz",
            );
            if (max($Salign_Result["TM1"], $Salign_Result["TM2"]) < 0.5 && min($Salign_Result["TM1"], $Salign_Result["TM2"]) < 0.334) continue;
            array_push($Salign_Results, $Salign_Result);
        }
        array_multisort(array_column($Salign_Results, "RMSD"), $Salign_Results);
        ?>
        <section class="main">
            <div style="display: block; width: 100%;">
                <h2 class="main_h2">
                    <?php
                    $Salign_Result_Num = count($Salign_Results);
                    if ($Salign_Result_Num == 0) {
                        echo " No result";
                    } else {
                        echo $Salign_Result_Num . " results";
                    }
                    ?>
                </h2>
                <HR id="hr1" color=#21262d SIZE=1>
                <br>
                <?php
                if ($Salign_Result_Num > 0) {
                    include "../page.php";
                    include "../display.php";
                    $Page_Info = page_info($Salign_Result_Num);
                    $Salign_Results_Displayed = array_slice($Salign_Results, $Page_Info["top"], $Page_Info["length"]);
                    foreach ($Salign_Results_Displayed as $Salign_Result) {
                        form_salign_result($Salign_Result);
                    }
                }
                ?>
            </div>
        </section>
        <?php
        if ($Salign_Result_Num > 0) {
            include "legend.php";
        }
        ?>
    </main>
    <script>
        function MainFunction() {
            var isExpanded = document.getElementsByClassName("msp-layout-expanded");
            var hr1 = document.getElementById("hr1");
            if (isExpanded.length==0) {
                hr1.style.visibility = "visible";
            } else hr1.style.visibility = "hidden";
            var mspSeqs = document.getElementsByClassName("msp-layout-top");
            for (var i=0;i<mspSeqs.length;i++){
                mspSeqs[i].remove();
            }
            setTimeout(() => {
                MainFunction()
            }, 100)
        }
        MainFunction();
    </script>
</body>

</html>