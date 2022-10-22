<section class="aside_right" style="float: right; background-color: transparent; overflow-y: auto;">
    <div style="padding: auto 24px; margin-top: 32px;">
        <h2 class="h2_aside">Page(s)</h2>
        <div style="padding: 8px 0; margin: 8px 0; margin-right: 10px; border-color: #21262d; border-bottom: 1px solid #30363d;">
            <form method="post">
                <?php
                for ($Page_i = 1; $Page_i <= $Page_Info["tot"]; $Page_i++) {
                    $CSS_Check_Page = " background-color: #30363d;";
                    if ($Page_Info["page"] == $Page_i) {
                        $CSS_Check_Page = " background-color: #0969da; pointer-events:none;";
                    }
                    echo "<button class='btn' style='margin-right:4px; margin-bottom:4px; width: 20%;$CSS_Check_Page' type='submit' name='page' value='$Page_i'>$Page_i</button>";
                }
                ?>
            </form>
        </div>
        <div style="padding: 8px 0; margin: 8px 0; margin-right: 10px; border-color: #21262d; border-bottom: 1px solid #30363d;">
            <span class="programming_lang-span">
                <span class="lang_color" style="background-color:rgb(220, 220, 220);"></span>
                <span>&nbsp;<strong>Query structure</strong></span>
            </span>
            <br>
            <span class="programming_lang-span">
                <span id="hit_color" class="lang_color" style="background-color:rgb(0, 83, 214);"></span>
                <span>&nbsp;<strong>Hit structure</strong></span>
            </span>
        </div>
    </div>
</section>
<script>
    function ChangeColor() {
        var hitColor = document.getElementById("hit_color");
        var plddtColors = ["rgb(0, 83, 214)", "rgb(101, 203, 243)", "rgb(255, 219, 19)", "rgb(255, 125, 69)"];
        var randomColor = hitColor.style.backgroundColor;
        while (randomColor == hitColor.style.backgroundColor) {
            randomColor = plddtColors[Math.floor(Math.random() * plddtColors.length)];
        }
        hitColor.style.backgroundColor = randomColor; //alert(randomColor);
        setTimeout(() => {
            ChangeColor()
        }, 1000)
    }
    ChangeColor();
</script>