<?php
$Data_URL = getenv("MP_REPO_PATH") . $_GET["repo"] . '/' . $_GET["name"];
echo md5(file_get_contents($Data_URL));