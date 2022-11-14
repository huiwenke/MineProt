<?php

function cache_clear($File_Path, $Repo, $Force)
{
    if (strstr($File_Path, "MP_BROWSE_$Repo")){
        $md5_Repo_Time = md5(filemtime(getenv("MP_REPO_PATH") . $Repo));
        if (strstr($File_Path, $md5_Repo_Time)&&(!$Force)) return;
        unlink($File_Path);
    }
}

$Files = array_diff(scandir(sys_get_temp_dir()), array('.', '..'));
foreach ($Files as $File){
    $File_Path = sys_get_temp_dir() . '/' . $File;
    cache_clear($File_Path, $_GET["repo"], $_GET["force"]);
}