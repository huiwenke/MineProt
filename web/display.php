<?php

function form_repo($Data_Repo)
{
    $html_Checked = "";
    if (array_key_exists("search", $_GET)) {
        if (!array_key_exists("repo", $_GET) || in_array($Data_Repo, $_GET["repo"])) $html_Checked = " checked";
    } else if (array_key_exists("repo", $_GET) && $Data_Repo == $_GET["repo"]) $html_Checked = " checked";
    print <<<EOT
    <ul>
        <li>
            <div class="list-item-div">
                <input type="checkbox" id="$Data_Repo" value="$Data_Repo" name="repo[]" class="a-item-div"$html_Checked>
                <label for="$Data_Repo">
                    <font color="white">$Data_Repo</font>
                </label>
            </div>
        </li>
    </ul>
EOT;
}

function form_viewer($Search_Result)
{
    $Search_Result_Viewer = "MP_" . md5($Search_Result["_source"]["name"]);
    $Search_Result_Path = "./api/file/" . $Search_Result["_index"] . '/' . $Search_Result["_source"]["name"] . ".cif";
    print <<<EOT
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    .msp-plugin ::-webkit-scrollbar-thumb {
        background-color: #474748 !important;
    }

    .viewerSection {
        margin: 120px 0 0 0;
    }

    #$Search_Result_Viewer {
        float: center;
        width: 100%;
        height: 50vh;
        position: relative;
        z-index: 31;
    }
</style>
<div class="viewerSection">
    <!-- Molstar container -->
    <div id="$Search_Result_Viewer"></div>

</div>
<script>
    //Create plugin instance
    var viewerInstance = new PDBeMolstarPlugin();

    //Set options (Checkout available options list in the documentation)
    var options = {
        customData: {
            url: '$Search_Result_Path',
            format: 'cif'
        },
        alphafoldView: true,
        bgColor: {
            r: 255,
            g: 255,
            b: 255
        },
        hideCanvasControls: ['selection', 'animation', 'controlToggle', 'controlInfo']
    }

    var viewerContainer = document.getElementById('$Search_Result_Viewer');

    viewerInstance.render(viewerContainer, options);
</script>
EOT;
}

function form_search_result($Search_Result)
{
    $b64_Data_URL = base64_encode(getenv("MP_LOCALHOST") . "/api/file/" . $Search_Result["_index"] . '/' . $Search_Result["_source"]["name"] . ".json");
    if ($Search_Result["_source"]["anno"]["homolog"] == "") {
        $html_Homolog_Info = "none";
    } else if ($Search_Result["_source"]["anno"]["database"] == "afdb") {
        $html_Homolog_Info = '
        <a class="card-link user-properties-link" href="https://alphafold.com/search/text/' . $Search_Result["_source"]["anno"]["homolog"] . '">' . $Search_Result["_source"]["anno"]["homolog"] . '</a>: ' . $Search_Result["_source"]["anno"]["description"][0];
    } else {
        $html_Homolog_Info = '
        <a class="card-link user-properties-link" href="https://www.uniprot.org/' . $Search_Result["_source"]["anno"]["database"] . '?query=' . $Search_Result["_source"]["anno"]["homolog"] . '">' . $Search_Result["_source"]["anno"]["homolog"] . '</a>: ' . $Search_Result["_source"]["anno"]["description"][0];
    }
    print <<<EOT
<div class="card-inner-div">
    <div>
        <div style="margin-left: 16px; width=100%;">
            <strong style="color:#c9d1d9; margin-top: 7px;">{$Search_Result["_source"]["name"]}</strong>
            <div style="color:#c9d1d9; margin-top: 7px;">
                Similar to {$html_Homolog_Info}                
            </div>
            <br>
            <span name="search_result_link" id="/api/file/{$Search_Result["_index"]}/{$Search_Result["_source"]["name"]}.cif">
		        <a href="./api/file/{$Search_Result["_index"]}/{$Search_Result["_source"]["name"]}.pdb" style="width: 10%; background-color: rgb(0, 83, 214);" class="btn"><center>PDB</center></a>
		        <a href="./api/file/{$Search_Result["_index"]}/{$Search_Result["_source"]["name"]}.cif" style="width: 10%; background-color: rgb(0, 83, 214);" class="btn"><center>CIF</center></a>
                <a href="./api/file/{$Search_Result["_index"]}/{$Search_Result["_source"]["name"]}.json" style="width: 20%; background-color: #563d7c;" class="btn"><center>Score (JSON)</center></a>
                <a target="_blank" href="./api/plot/pae.php?data_url={$b64_Data_URL}" style="width: 15%; background-color: #fd1593;" class="btn"><center>PAE plot</center></a>
	        </span>
        </div>
    </div>
EOT;
    form_viewer($Search_Result);
    echo "
</div>
<br>";
}

function form_td($Table_tr)
{
    echo "<tr>";
    $Name = $Table_tr["name"];
    $Data_Repo = $Table_tr["repo"];
    echo "
    <td style='word-wrap: break-word; word-break: break-all; width: 20%;'>
        <a style='color: #161b22;' class='user-properties-link' href='search.php?search=$Name&repo[]=$Data_Repo' target='_blank'>
        <strong>" . $Name . "</strong>
        </a>
    </td>";
    echo "
    <td>
        <a class='btn' style='background-color: #800080;' href='./api/file/$Data_Repo/$Name.pdb'>
        PDB
        </a>
        <a class='btn' style='background-color: #800080;' href='./api/file/$Data_Repo/$Name.cif'>
        CIF
        </a>
    </td>";
    $Scores_pLDDT = $Table_tr["plddt"];
    if ($Scores_pLDDT >= 90) {
        $pLDDT_Color = "background-color:rgb(0, 83, 214);";
    } else if ($Scores_pLDDT >= 70) {
        $pLDDT_Color = "background-color:rgb(101, 203, 243);";
    } else if ($Scores_pLDDT >= 50) {
        $pLDDT_Color = "background-color:rgb(255, 219, 19);";
    } else $pLDDT_Color = "background-color:rgb(255, 125, 69);";
    if ($Scores_pLDDT <= 0) echo "<td>N/A</td>";
    else echo "<td style='color:white; $pLDDT_Color'>" . number_format($Scores_pLDDT, 2) . "</td>";
    if (file_exists(getenv("MP_REPO_PATH") . $Data_Repo . '/' . $Name . ".a3m") || file_exists(getenv("MP_REPO_PATH") . $Data_Repo . '/' . $Name . ".a3m.gz")) {
        $A3M_Url = "<a class='btn' style='background-color: #DC143C;' href='./api/file/$Data_Repo/$Name.a3m'>A3M</a>";
    } else $A3M_Url = "N/A";
    echo "<td>$A3M_Url</td>";
    $Homolog = $Table_tr["homolog"];
    $Database = $Table_tr["database"];
    $Annotation = $Table_tr["anno"];
    if ($Database == "afdb") $Homo_Url = "https://alphafold.com/search/text/" . $Homolog;
    else $Homo_Url = "https://www.uniprot.org/$Database?query=$Homolog";
    echo "
    <td style='word-wrap: break-word; width: 50%;'>
        <a target='_blank' title='Similar to $Homolog' style='color: #161b22;' class='user-properties-link' href='$Homo_Url'>
        $Annotation
        </a>
    </td>";
    echo "</tr>";
}

function form_saligner($Salign_Result)
{
    $Salign_Result_Viewer = "MP_" . md5($Salign_Result["PDB1"]);
    $Salign_Name = pathinfo($Salign_Result["PDB2"])["filename"];
    $Salign_Repo = pathinfo(dirname($Salign_Result["PDB2"]))["filename"];
    $Salign_Result_Path = "../api/file/" . $Salign_Repo . '/' . $Salign_Name . ".cif";
    $Salign_Query_Path = "../api/cache/get.php?data_url=" . base64_encode($Salign_Result["PDB1"] . ".pdb");
    print <<<EOT
<style>
.msp-plugin {
    margin: 0 0 0 0;
}
#$Salign_Result_Viewer {
    float: center;
    width: 100%;
    height: 50vh;
    position: relative;
    z-index: 31;
}
</style>
<div id="$Salign_Result_Viewer"></div>
<script>
    //Create plugin instance
    var $Salign_Result_Viewer = new PDBeMolstarPlugin();

    //Set options (Checkout available options list in the documentation)
    var options = {
        alphafoldView: true,
        customData: {
            url: '$Salign_Query_Path',
            format: "pdb"
        }
    }

    var viewerContainer = document.getElementById('$Salign_Result_Viewer');

    $Salign_Result_Viewer.render(viewerContainer, options);
    $Salign_Result_Viewer.visual.update({alphafoldView: true, customData: {url: '$Salign_Result_Path', format: "cif"}}, false);
</script>
EOT;
}

function form_salign_result($Salign_Result)
{
    $Salign_Name = pathinfo($Salign_Result["PDB2"])["filename"];
    $Salign_Repo = pathinfo(dirname($Salign_Result["PDB2"]))["filename"];
    $Salign_Result_Data_URLs = array(
        "pdb" => base64_encode($Salign_Result["PDB1"] . ".pdb"),
        "hit" => "../api/file/" . $Salign_Repo . '/' . $Salign_Name . ".pdb",
        "pml" => base64_encode($Salign_Result["PDB1"] . ".pml"),
        "all" => base64_encode($Salign_Result["PDB1"] . "_all.pml"),
        "all_atm" => base64_encode($Salign_Result["PDB1"] . "_all_atm.pml"),
        "all_atm_lig" => base64_encode($Salign_Result["PDB1"] . "_all_atm_lig.pml"),
        "atm" => base64_encode($Salign_Result["PDB1"] . "_atm.pml")
    );
    $PDB1_Path = base64_encode(sys_get_temp_dir() . '/' . $Salign_Result["PDB1"] . ".pdb");
    $PDB2_Path = base64_encode($Salign_Result["PDB2"]);
    print <<<EOT
    <div class="card-inner-div">
        <div>
            <div style="width=100%;">
                <strong><a target='_blank' class='user-properties-link' style="color:#c9d1d9; margin-top: 7px;" href="../search.php?search={$Salign_Name}&repo[]={$Salign_Repo}">{$Salign_Name}</a></strong>
                <br><br>
                <span>
                    <a target="_blank" href="../api/cache/get.php?download=true&data_url={$Salign_Result_Data_URLs["pdb"]}" style="background-color: rgb(0, 83, 214);" class="btn"><center>query.pdb</center></a>
                    <a target="_blank" href="{$Salign_Result_Data_URLs["hit"]}" style="background-color: #fd1593;" class="btn"><center>hit.pdb</center></a>
                    <a target="_blank" href="../api/cache/get.php?download=true&data_url={$Salign_Result_Data_URLs["pml"]}" style="background-color: #563d7c;" class="btn"><center>query.pml</center></a>
                    <a target="_blank" href="../api/cache/get.php?download=true&data_url={$Salign_Result_Data_URLs["all"]}" style="background-color: #563d7c;" class="btn"><center>all.pml</center></a>
                    <a target="_blank" href="../api/cache/get.php?download=true&data_url={$Salign_Result_Data_URLs["all_atm"]}" style="background-color: #563d7c;" class="btn"><center>all_atm.pml</center></a>
                    <a target="_blank" href="../api/cache/get.php?download=true&data_url={$Salign_Result_Data_URLs["all_atm_lig"]}" style="background-color: #563d7c;" class="btn"><center>all_atm_lig.pml</center></a>
                    <a target="_blank" href="../api/cache/get.php?download=true&data_url={$Salign_Result_Data_URLs["atm"]}" style="background-color: #563d7c;" class="btn"><center>atm.pml</center></a>
	            </span>
                <br><br>
                <table style="font-size:12px;">
                    <thead>
                        <tr>
                            <th style='width: 16.7%;'>RMSD</th>
                            <th style='width: 16.7%;'>TM1</th>
                            <th style='width: 16.7%;'>TM2</th>
                            <th style='width: 16.7%;'>IDali</th>
                            <th style='width: 16.7%;'>ID1</th>
                            <th style='width: 16.7%;'>ID2</th>
                            <th style='width: 16.7%;'>Detail</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>{$Salign_Result["RMSD"]}</td>
                            <td>{$Salign_Result["TM1"]}</td>
                            <td>{$Salign_Result["TM2"]}</td>
                            <td>{$Salign_Result["IDali"]}</td>
                            <td>{$Salign_Result["ID1"]}</td>
                            <td>{$Salign_Result["ID2"]}</td>
                            <td><a class='btn' style='background-color: #DC143C;' target="_blank" href="./detail.php?pdb1={$PDB1_Path}&pdb2={$PDB2_Path}">▶</a></td>
                        </tr>
                    </tbody>
                </table>
                <br>
            </div>
        </div>
EOT;
    form_saligner($Salign_Result);
    print <<<EOT
    </div>
<br>
EOT;
}
