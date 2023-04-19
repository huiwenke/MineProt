<?php
if (file_exists($File_Path)){
    echo gzdecode(file_get_contents($File_Path));
}