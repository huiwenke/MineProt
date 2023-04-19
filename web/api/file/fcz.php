<?php
$Curl_Handle = curl_init(getenv("MP_LOCALHOST") . "/api/fcz2pdb/");
curl_setopt($Curl_Handle, CURLOPT_RETURNTRANSFER, 1);
$Curl_Data = array(
    "file" => new CURLFile($File_Path),
);
curl_setopt($Curl_Handle, CURLOPT_POSTFIELDS, $Curl_Data);
$Response = curl_exec($Curl_Handle);
curl_close($Curl_Handle);
echo $Response;