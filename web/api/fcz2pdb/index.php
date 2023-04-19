<?php

/*
Convert FCZ to PDB.
Request: FCZ content
Response: PDB text
*/

putenv("PATH=" . getenv("PATH"));
$FCZ = file_get_contents($_FILES['file']['tmp_name']);
$FCZ_Path = sys_get_temp_dir() . '/' . md5($FCZ) . ".fcz";
$PDB_Path = sys_get_temp_dir() . '/' . md5($FCZ) . ".pdb";
file_put_contents($FCZ_Path, $FCZ);
shell_exec("foldcomp decompress $FCZ_Path $PDB_Path");
$PDB = file_get_contents($PDB_Path);
echo $PDB;
unlink($FCZ_Path);
unlink($PDB_Path);
