<?php
header('Content-Type:application/json');
$Results = array();

$Search_Term = base64_decode($Request_Term);
$Query = array(
    "query" => array(
        "match_phrase" => array(
            "anno.description" => $Search_Term
        )
    ),
    "size" => 200
);
$Query_Json = json_encode($Query);
$Curl_Handle = curl_init(getenv("MP_ELASTICSEARCH") . "/$Dataset/_search");
curl_setopt($Curl_Handle, CURLOPT_POSTFIELDS, $Query_Json);
curl_setopt(
    $Curl_Handle,
    CURLOPT_HTTPHEADER,
    array(
        "Content-Type: application/json"
    )
);
curl_setopt($Curl_Handle, CURLOPT_RETURNTRANSFER, 1);
$Response_Json = curl_exec($Curl_Handle);
curl_close($Curl_Handle);
$Hits = json_decode($Response_Json, true);
foreach ($Hits["hits"]["hits"] as $Hit) {
    array_push($Results, $Hit);
}
echo json_encode($Results);
