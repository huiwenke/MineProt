<?php
$File_Path = sys_get_temp_dir() . '/' . base64_decode($_GET["data_url"]);
if (strpos($File_Path, "..")) {
    echo "?";
    exit;
}
if ($_GET["download"] == "") {
    echo file_get_contents($File_Path);
} else {
    $File = fopen($File_Path, "rb");
    header("Content-type: application/octet-stream");
    header("Accept-Ranges: bytes");
    header("Accept-Length: " . filesize($File_Path));
    header("Content-Disposition: attachment; filename=" . pathinfo($File_Path)["basename"]);
    echo fread($File, filesize($File_Path));
    fclose($File);
    exit;
}
