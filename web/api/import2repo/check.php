<?php

/*
Check if file to upload already exists in target repository.
GET request:
    {
        "name": file name
        "repo": repository name
    }
Response: MD5 of file in query
*/

$Data_URL = getenv("MP_REPO_PATH") . $_GET["repo"] . '/' . $_GET["name"];
echo md5(file_get_contents($Data_URL));