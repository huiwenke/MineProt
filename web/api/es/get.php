<?php
header('Content-Type:application/json');
$_id = $Request_Term;
if ($_id == '') {
    $Curl_Handle = curl_init(getenv("MP_ELASTICSEARCH") . "/$Dataset");
} else $Curl_Handle = curl_init(getenv("MP_ELASTICSEARCH") . "/$Dataset/_doc/$_id");
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

echo $Response_Json;
