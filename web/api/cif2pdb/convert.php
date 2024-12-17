<?php
$TMP_DIR = sys_get_temp_dir() . '/' . md5($CIF);
shell_exec("mkdir $TMP_DIR");
$CIF_File_Path = "$TMP_DIR/$PROTEIN_NAME.cif";
$CIF_File = fopen($CIF_File_Path, 'w');
fwrite($CIF_File, $CIF);
fclose($CIF_File);

$PDB_File_Path = "$TMP_DIR/$PROTEIN_NAME.pdb";
putenv("RCSBROOT=" . getenv("RCSBROOT"));
putenv("PATH=" . getenv("PATH"));
shell_exec("maxit -input $CIF_File_Path -output $PDB_File_Path -o 2");
$PDB = file_get_contents($PDB_File_Path);
echo $PDB;

shell_exec("rm -rf $TMP_DIR");
