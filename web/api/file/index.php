<?php
header('Content-Type:application/json');
$Current_URL = explode('/', $_SERVER["REQUEST_URI"]);
$Dataset = $Current_URL[count($Current_URL) - 2];
$File_Name = $Current_URL[count($Current_URL) - 1];
$File_Type = pathinfo($File_Name)["extension"];
$File_Path = getenv("MP_REPO_PATH") . $Dataset . '/' . $File_Name;
include "$File_Type.php";
