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
$Search_Result_Path = "/release/" . $Search_Result["_index"] . '/' . $Search_Result["_source"]["name"] . ".cif";
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
print <<<EOT
<div class="card-inner-div">
    <div style="display: flex;">
        <div style="margin-left: 16px;">
            <strong style="color:#c9d1d9; margin-top: 7px;">{$Search_Result["_source"]["name"]}</strong>
            <div style="color:#c9d1d9; margin-top: 7px;">
                Similar to 
                <a class="card-link user-properties-link" href="https://www.uniprot.org/uniprotkb?query={$Search_Result["_source"]["anno"]["homolog"]}">
                    {$Search_Result["_source"]["anno"]["homolog"]}
                </a>
                : {$Search_Result["_source"]["anno"]["description"][0]}
            </div>
            <br>
            <span style="color: #8b949e;">
			    <a href="/release/{$Search_Result["_index"]}/{$Search_Result["_source"]["name"]}.pdb" style="width: 15%; background-color: rgb(0, 83, 214);" class="btn"><center>PDB</center></a>
			    <a href="/release/{$Search_Result["_index"]}/{$Search_Result["_source"]["name"]}.cif" style="width: 15%; background-color: rgb(0, 83, 214);" class="btn"><center>CIF</center></a>
                <a href="/release/{$Search_Result["_index"]}/{$Search_Result["_source"]["name"]}.json" style="width: 30%; background-color: #563d7c;" class="btn"><center>Score (JSON)</center></a>
		    </span>
        </div>
    </div>    
EOT;
form_viewer($Search_Result);
echo "</div><br>";
}
