<?php
$_id = $Request_Term;
if ($_id == '') {
    $Curl_Handle = curl_init("http://elasticsearch:9200/$Dataset");
} else $Curl_Handle = curl_init("http://elasticsearch:9200/$Dataset/_doc/$_id");
curl_setopt($Curl_Handle, CURLOPT_CUSTOMREQUEST, "DELETE");
curl_exec($Curl_Handle);
curl_close($Curl_Handle);
