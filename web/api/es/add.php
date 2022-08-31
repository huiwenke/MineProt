<?php
$_id = $Request_Term;
$Add_Json = file_get_contents("php://input");
$Curl_Handle = curl_init("http://elasticsearch:9200/$Dataset/_doc/$_id");
curl_setopt($Curl_Handle, CURLOPT_RETURNTRANSFER, 1);
curl_setopt($Curl_Handle, CURLOPT_POST, 1);
curl_setopt($Curl_Handle, CURLOPT_POSTFIELDS, $Add_Json);
curl_setopt($Curl_Handle, CURLOPT_HTTPHEADER, array(                                                                         
    "Content-Type: application/json")
);
curl_exec($Curl_Handle);
curl_close($Curl_Handle);