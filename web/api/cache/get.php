<?php
echo file_get_contents(sys_get_temp_dir() . '/' . base64_decode($_GET["data_url"]));
