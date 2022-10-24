<?php
include "../../api.php";

$Cache_Dirs = scandir(sys_get_temp_dir());
foreach ($Cache_Dirs as $Cache_Dir) {
    if (strpos($Cache_Dir, "MP_SALIGN") === 0) {
        $Cache_Path = sys_get_temp_dir() . '/' . $Cache_Dir;
        $Cache_Time = time()-filemtime($Cache_Path);
        if ($Cache_Time>86400){
            shell_exec("rm -rf $Cache_Path");
        }
    }
}

foreach ($DATA_REPOS as $Data_Repo) {
    shell_exec("curl http://MineNginx/browse.php?repo=$Data_Repo");
    shell_exec("curl -X POST -F 'sort=plddt' http://MineNginx/browse.php?repo=$Data_Repo");
}