<?php
$Current_USalign_Num = shell_exec("ls $TMP_DIR/*_all_atm_lig.pml | wc -l");
$Total_USalign_Num = shell_exec("cat $TMP_DIR/query.sh | wc -l");
?>
<section class="main_salign">
    <div style="display: block; width: 100%;">
        <center>
            <h1 style="margin-bottom: 8px; color:#efefef;">Searching...</h1>
        </center>
        <center>
            <progress value=<?php echo $Current_USalign_Num; ?> max=<?php echo $Total_USalign_Num; ?>></progress>
        </center>
    </div>
</section>