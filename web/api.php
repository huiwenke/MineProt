<?php
function search_api($Search_Repos, $Search_Term)
{
    $b64_Search_Term = base64_encode($Search_Term);
    $Curl_Handle = curl_init("http://MineNginx/api/es/$Search_Repos/search/$b64_Search_Term");
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
