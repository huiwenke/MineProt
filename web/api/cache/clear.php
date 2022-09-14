<?php

function cache_clear($File)
{
    if (file_exists($File)) {
        unlink($File);
    }
}

$ob_File = sys_get_temp_dir() . "/MP_BROWSE_" . md5($_GET["repo"] . filemtime(getenv("MP_REPO_PATH") . $_GET["repo"])) . '_';
cache_clear($ob_File);
cache_clear($ob_File . "plddt");