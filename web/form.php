<?php
$Data_Repos = array_diff(scandir("/var/www/data"), array('.', '..'));
?>
<section id="aside" class="aside" style="display: inline-flex;">
    <div class="child">
        <form action="search.php" method="get">
            <div style="margin-bottom: 16px; margin-top: 8px;">
                <label class="wrapper">
                    <input name="search" class="form-control-header" placeholder="Enter keywords..." required>
                </label>
            </div>
            <div style="margin-bottom: 16px; margin-top: 8px;"></div>
            <h2 class="h2_aside">
                Protein Repositories
            </h2>
            <div style="margin-bottom: 16px; margin-top: 8px;"></div>
            <?php
            foreach ($Data_Repos as $Data_Repo) {
                echo '
                <ul>
                    <li>
                        <div class="list-item-div">
                            <input type="checkbox" id="' . $Data_Repo . '" value="' . $Data_Repo . '" name="repo[]" class="a-item-div">
                            <label for="' . $Data_Repo . '">
                                <font color="white">' . $Data_Repo . '</font>
                            </label>
                        </div>
                    </li>
                </ul>
                ';
            }
            ?>
            <div style="margin-bottom: 16px; margin-top: 8px;"></div>
            <button class="btn" type="submit">Search</button>
        </form>
    </div>
</section>