<?php
$Current_URL = explode('/', $_SERVER["REQUEST_URI"]);
$Dataset = $Current_URL[count($Current_URL) - 3];
$Request_Type = $Current_URL[count($Current_URL) - 2];
$Request_Term = $Current_URL[count($Current_URL) - 1];
include "$Request_Type.php";
