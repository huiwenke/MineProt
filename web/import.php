<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>import</title>
    <link rel="shortcut icon" type="image/png" href="/assets/img/logo.png">
    <link rel="stylesheet" type="text/css" href="/assets/css/style.css">
    <link rel="stylesheet" type="text/css" href="/assets/css/github-dark.min.css">
    <script src="/assets/js/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>
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
                <HR color=#21262d SIZE=1.5>
                <h3 style="margin-bottom: 8px; color:#efefef;">ColabFold</h3>
                <pre><code class="language-bash">git clone http://git.bmeonline.cn/218818/mineprot.git
cd mineprot
scripts/colabfold/import.sh [--relax] [--zip] --name-mode [0|1|2|3] --repo [Repo Name] path/to/data</code></pre>
            </div>
        </section>
    </main>
</body>

</html>