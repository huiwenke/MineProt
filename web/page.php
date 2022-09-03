<?php
function page_info($Search_Result_Num)
{
    $page = $_POST['page'];
    if ($page == '') {
        $page = 1;
    }
    $length = 10;
    $top = ($page - 1) * $length;
    $tot = (int)($Search_Result_Num / $length);
    if ($Search_Result_Num % $length != 0) {
        $tot = $tot + 1;
    }
    $Page_Info = array("page" => $page, "top" => $top, "tot" => $tot, "length" => $length);
    return $Page_Info;
}
