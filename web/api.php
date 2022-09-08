<?php
function search_api($Search_Repos, $Search_Term)
{
    $b64_Search_Term = base64_encode($Search_Term);
    $Curl_Handle = curl_init($_ENV["MP_LOCALHOST"] . "/api/es/$Search_Repos/search/$b64_Search_Term");
    curl_setopt($Curl_Handle, CURLOPT_RETURNTRANSFER, 1);
    curl_setopt(
        $Curl_Handle,
        CURLOPT_HTTPHEADER,
        array(
            "Content-Type: application/json"
        )
    );
    $Response_Json = curl_exec($Curl_Handle);
    curl_close($Curl_Handle);
    return $Response_Json;
}

function get_api_tr($Data_Repo, $File)
{
    $Result = array("name" => pathinfo($File)["filename"], "repo" => $Data_Repo, "plddt" => 0.0, "anno" => "", "homolog" => "");
    $Scores = json_decode(file_get_contents($_ENV["MP_REPO_PATH"] . $Data_Repo . '/' . $File), true);
    $Result["plddt"] = array_sum($Scores["plddt"]) / count($Scores["plddt"]);
    $b64_Name = base64_encode($Result["name"]);
    $ES_Get = json_decode(file_get_contents($_ENV["MP_LOCALHOST"] . "/api/es/$Data_Repo/get/$b64_Name"), true);
    $Result["homolog"] = $ES_Get["_source"]["anno"]["homolog"];
    $Result["anno"] = $ES_Get["_source"]["anno"]["description"][0];
    return $Result;
}
