<?php

/*
Convert CIF to PDB.
JSON request:
    {
        "name": protein name
        "data": base64-encoded CIF text
    }
Response: PDB text
*/

$CIF_Raw_Data = file_get_contents("php://input");
$PROTEIN_NAME = json_decode($CIF_Raw_Data, true)["name"];
$CIF = base64_decode(json_decode($CIF_Raw_Data, true)["data"]);
include "convert.php";
