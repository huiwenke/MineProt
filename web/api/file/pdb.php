<?php
if (file_exists($File_Path)) {
    echo file_get_contents($File_Path);
} else {
    if (file_exists($File_Path . ".gz")) {
        $File_Path = $File_Path . ".gz";
        include "gz.php";
    } else {
        if (file_exists(str_replace(".pdb", ".fcz", $File_Path))) {
            $File_Path = str_replace(".pdb", ".fcz", $File_Path);
            include "fcz.php";
        }
    }
}
