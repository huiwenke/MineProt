<?php
if (file_exists($File_Path)){
    echo file_get_contents($File_Path);
} else {
    $File_Path = $File_Path . ".gz";
    include "gz.php";
}
