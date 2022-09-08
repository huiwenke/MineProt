<?php
$_id = $Request_Term;
if ($_id == '') {
    $Curl_Handle = curl_init($_ENV["MP_ELASTICSEARCH"] . "/$Dataset");
} else $Curl_Handle = curl_init($_ENV["MP_ELASTICSEARCH"] . "/$Dataset/_doc/$_id");
curl_setopt($Curl_Handle, CURLOPT_CUSTOMREQUEST, "DELETE");
curl_exec($Curl_Handle);
curl_close($Curl_Handle);
