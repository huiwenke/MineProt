<?php
header('Content-Type:application/json');
$_id = $Request_Term;

$Curl_Handle = curl_init($_ENV["MP_ELASTICSEARCH"] . "/$Dataset/_doc/$_id");
curl_setopt($Curl_Handle, CURLOPT_RETURNTRANSFER, 1);
curl_setopt($Curl_Handle, CURLOPT_HTTPHEADER, array(                                                                         
    "Content-Type: application/json")
);
$Response_Json = curl_exec($Curl_Handle);
curl_close($Curl_Handle);

echo $Response_Json;
