<?php
include "../../api.php";

$Result_ID = uniqid();
$RMSD = $_POST["rmsd"];
$TMP_DIR = sys_get_temp_dir() . "/MP_SALIGN_" . $Result_ID;
mkdir($TMP_DIR);

if (array_key_exists("repo", $_POST)) {
    $Search_Repos = $_POST["repo"];
} else $Search_Repos = $DATA_REPOS;
foreach ($Search_Repos as $Search_Repo) {
    mkdir($TMP_DIR . '/' . $Search_Repo);
}

$PDB_List = array();
if ($_POST["search"] != '') {
    $Search_Results_Json = search_api(implode(',', $Search_Repos), $_POST["search"]);
    $Search_Results = json_decode($Search_Results_Json, true);
    foreach ($Search_Results as $Search_Result) {
        $PDB_URL = getenv("MP_LOCALHOST") . "/api/file/" . $Search_Result["_index"] . '/' . $Search_Result["_source"]["name"] . ".pdb";
        $PDB = file_get_contents($PDB_URL);
        $PDB_Path = $TMP_DIR . '/' . $Search_Result["_index"] . '/' . $Search_Result["_source"]["name"] . ".pdb";
        file_put_contents($PDB_Path, $PDB);
        array_push($PDB_List, $PDB_Path);
    }
} else {
    foreach ($Search_Repos as $Search_Repo) {
        $Files = array_diff(scandir(getenv("MP_REPO_PATH") . $Search_Repo), array('.', '..'));
        foreach ($Files as $File) {
            if (pathinfo($File)["extension"] == "pdb") {
                array_push($PDB_List, getenv("MP_REPO_PATH") . $Search_Repo . '/' . $File);
            }
        }
    }
}

$Query_PDB_Path = $TMP_DIR . "/query.pdb";
file_put_contents($Query_PDB_Path, $_POST["structure"]);
$Shell_Script_Path = $TMP_DIR . "/query.sh";
$Shell_Script = fopen($Shell_Script_Path, 'w');
foreach ($PDB_List as $PDB_Path) {
    $Result_Prefix = $TMP_DIR . "/query_" . pathinfo($PDB_Path)["filename"];
    $Shell_CMD = "USalign $Query_PDB_Path $PDB_Path -outfmt 2 -o $Result_Prefix\n";
    fwrite($Shell_Script, $Shell_CMD);
}
$TMP_STR = str_replace("/", "\\/", $TMP_DIR);
fwrite($Shell_Script, "sed -i 's/$TMP_STR\///' $TMP_DIR/*.pml\n");
$TMP_STR = str_replace("/", "\\/", getenv("MP_REPO_PATH"));
fwrite($Shell_Script, "sed -i 's/$TMP_STR.*\///' $TMP_DIR/*.pml\n");
fwrite($Shell_Script, "touch $TMP_DIR/done.txt");
fclose($Shell_Script);
putenv("PATH=" . getenv("PATH"));
shell_exec("/bin/bash $Shell_Script_Path > $TMP_DIR/query.out &");
echo $Result_ID;
header("location: ../../salign/result.php?rid=$Result_ID&rmsd=$RMSD");
exit;
