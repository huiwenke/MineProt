<?php
if (file_exists($File_Path)) {
    echo file_get_contents($File_Path);
} else {
    if (file_exists($File_Path . ".gz")) {
        $File_Path = $File_Path . ".gz";
        include "gz.php";
    } else {
        $PDB_ID = str_replace(".cif", "", $File_Name);
        $PDB_URL = getenv("MP_LOCALHOST") . "/api/file/" . $Dataset . '/' . $PDB_ID . ".pdb";
        $Curl_Data = array(
            "name" => $PDB_ID,
            "data" => base64_encode(file_get_contents($PDB_URL)),
        );
        $Query_Json = json_encode($Curl_Data);
        $Curl_Handle = curl_init(getenv("MP_LOCALHOST") . "/api/pdb2alphacif/");
        curl_setopt($Curl_Handle, CURLOPT_POSTFIELDS, $Query_Json);
        curl_setopt($Curl_Handle, CURLOPT_RETURNTRANSFER, 1);
        $Response = curl_exec($Curl_Handle);
        curl_close($Curl_Handle);
        echo $Response;
    }
}
