<?php
$DATA_REPOS = array_diff(scandir("/var/www/data"), array('.', '..'));
?>
<section id="aside" class="aside" style="display: inline-flex;">
    <div class="child">
        <form action="search.php" method="get">
            <div style="margin-bottom: 16px; margin-top: 8px;">
                <label class="wrapper">
                    <input name="search" class="form-control-header" placeholder="🔍︎ Enter keywords..." required>
                </label>
            </div>
            <div style="margin-bottom: 16px; margin-top: 8px;"></div>
            <h2 class="h2_aside">
                Protein Repositories
            </h2>
            <div style="margin-bottom: 16px; margin-top: 8px;"></div>
            <?php
            include "display.php";
            foreach ($DATA_REPOS as $Data_Repo) {
                form_repo($Data_Repo);
            }
            ?>
            <div style="margin-bottom: 16px; margin-top: 8px;"></div>
            <button class="btn" type="submit" style="width: 50%;"><strong>Search</strong></button>
        </form>
    </div>
</section>