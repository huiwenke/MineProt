<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>import</title>
    <link rel="shortcut icon" type="image/png" href="/assets/img/logo.png">
    <link rel="stylesheet" type="text/css" href="/assets/css/style.css">
</head>

<body>
    <?php
    include "header.php";
    ?>
    <main style="min-height: 100vh;">
        <?php
        include "form.php";
        ?>
        <section class="main">
            <div style="display: block; width: 100%;">
                <h1 style="margin-bottom: 8px; color:#efefef;">Import</h1>
                <HR color=#21262d SIZE=1.5><br>
                <div class="card-inner-div" style="color:#efefef;">
                    <p>cd /path/to/mineprot</p>
                    <p>python3 scripts/colabfold/transform.py -n 1 -z -r -i /path/to/folder -o data/repo/xxx</p>
                    <p>python3 scripts/import2es.py -i data/repo/xxx -a</p>
                </div>
            </div>
        </section>
    </main>
</body>

</html>