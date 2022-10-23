<?php
putenv("PATH=" . getenv("PATH"));
$PDB1_Path = base64_decode($_GET["pdb1"]);
$PDB2_Path = base64_decode($_GET["pdb2"]);
$Details = shell_exec("USalign $PDB1_Path $PDB2_Path");
?>
<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Detail</title>
    <link rel="shortcut icon" type="image/png" href="../assets/img/logo.png">
    <link rel="stylesheet" type="text/css" href="../assets/css/github-dark.min.css">
    <script src="../assets/js/highlight.min.js"></script>
</head>

<body>
    <pre style="font-size: 16px; font-weight: 500;"><code class="language-bash"><?php echo $Details; ?></code></pre>
    <script>
        hljs.highlightAll();
    </script>
</body>

</html>