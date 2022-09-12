<?php

function form_repo($Data_Repo)
{
    print <<<EOT
    <ul>
        <li>
            <div class="list-item-div">
                <input type="checkbox" id="$Data_Repo" value="$Data_Repo" name="repo[]" class="a-item-div">
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
    $Search_Result_Path = "/repo/" . $Search_Result["_index"] . '/' . $Search_Result["_source"]["name"] . ".cif";
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
    $b64_Data_URL = base64_encode(getenv("MP_REPO_PATH") . $Search_Result["_index"] . '/' . $Search_Result["_source"]["name"] . ".json");
    if ($Search_Result["_source"]["anno"]["homolog"] == "") {
        $html_Homolog_Info = "none";
    } else {
        $html_Homolog_Info = '
        <a class="card-link user-properties-link" href="https://www.uniprot.org/uniprotkb?query=' . $Search_Result["_source"]["anno"]["homolog"] . '">' . $Search_Result["_source"]["anno"]["homolog"] . '</a>: ' . $Search_Result["_source"]["anno"]["description"][0];
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
            <span>
		        <a href="/repo/{$Search_Result["_index"]}/{$Search_Result["_source"]["name"]}.pdb" style="width: 10%; background-color: rgb(0, 83, 214);" class="btn"><center>PDB</center></a>
		        <a href="/repo/{$Search_Result["_index"]}/{$Search_Result["_source"]["name"]}.cif" style="width: 10%; background-color: rgb(0, 83, 214);" class="btn"><center>CIF</center></a>
                <a href="/repo/{$Search_Result["_index"]}/{$Search_Result["_source"]["name"]}.json" style="width: 20%; background-color: #563d7c;" class="btn"><center>Score (JSON)</center></a>
                <a target="_blank" href="/api/plot/pae.php?data_url={$b64_Data_URL}" style="width: 15%; background-color: #fd1593;" class="btn"><center>PAE plot</center></a>
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
        <a class='btn' style='background-color: #800080;' href='/repo/$Data_Repo/$Name.pdb'>
        PDB
        </a>
        <a class='btn' style='background-color: #800080;' href='/repo/$Data_Repo/$Name.cif'>
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
    echo "<td style='color:white; $pLDDT_Color'>" . number_format($Scores_pLDDT, 2) . "</td>";
    echo "
    <td>
        <a class='btn' style='background-color: #DC143C;' href='/repo/$Data_Repo/$Name.a3m'>
        A3M
        </a>
    </td>";
    $Homolog = $Table_tr["homolog"];
    $Annotation = $Table_tr["anno"];
    echo "
    <td style='word-wrap: break-word; width: 50%;'>
        <a target='_blank' title='Similar to $Homolog' style='color: #161b22;' class='user-properties-link' href='https://www.uniprot.org/uniprotkb?query=$Homolog'>
        $Annotation
        </a>
    </td>";
    echo "</tr>";
}
