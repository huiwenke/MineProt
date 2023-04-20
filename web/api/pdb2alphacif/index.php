<?php

/*
Convert PDB to CIF.
JSON request:
    {
        "name": protein name
        "data": base64-encoded PDB text
    }
Response: CIF text
*/

$PDB_Raw_Data = file_get_contents("php://input");
$PROTEIN_NAME = json_decode($PDB_Raw_Data, true)["name"];
$PDB = base64_decode(json_decode($PDB_Raw_Data, true)["data"]);
include "convert.php";
