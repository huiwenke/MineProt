<?php
function get_api_repo($Data_Repo)
{
    $Curl_Handle = curl_init(getenv("MP_LOCALHOST") . "/api/es/$Data_Repo/get/");
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
    if (strstr($Response_Json, "index_not_found_exception")) {
        return false;
    } else return true;
}

function search_api($Search_Repos, $Search_Term)
{
    $b64_Search_Term = base64_encode($Search_Term);
    $Curl_Handle = curl_init(getenv("MP_LOCALHOST") . "/api/es/$Search_Repos/search/$b64_Search_Term");
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

function get_api_tr($Data_Repo, $File_Name)
{
    $Result = array("name" => $File_Name, "repo" => $Data_Repo, "plddt" => -1.0, "anno" => "", "homolog" => "");
    $b64_Name = base64_encode($Result["name"]);
    $ES_Get = json_decode(file_get_contents(getenv("MP_LOCALHOST") . "/api/es/$Data_Repo/get/$b64_Name"), true);
    $Result["homolog"] = $ES_Get["_source"]["anno"]["homolog"];
    $Result["database"] = $ES_Get["_source"]["anno"]["database"];
    $Result["anno"] = $ES_Get["_source"]["anno"]["description"][0];
    $Result["plddt"] = $ES_Get["_source"]["score"];
    return $Result;
}

$DATA_REPOS = array_diff(scandir(getenv("MP_REPO_PATH")), array('.', '..'));
foreach ($DATA_REPOS as $Data_Repo_k => $Data_Repo) {
    if (!get_api_repo($Data_Repo)) {
        unset($DATA_REPOS[$Data_Repo_k]);
    }
}