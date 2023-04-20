<?php
if (file_exists($File_Path)) {
    echo file_get_contents($File_Path);
} else {
    if (file_exists($File_Path . ".gz")) {
        $File_Path = $File_Path . ".gz";
        include "gz.php";
    } else {
        $PROTEIN_NAME = str_replace(".cif", "", $File_Name);
        $PDB_URL = getenv("MP_LOCALHOST") . "/api/file/" . $Dataset . '/' . $PROTEIN_NAME . ".pdb";
        $PDB = file_get_contents($PDB_URL);
        include "../pdb2alphacif/convert.php";
    }
}
