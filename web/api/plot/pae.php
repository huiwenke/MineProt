<?php
$Data_URL = base64_decode($_GET["data_url"]);
$Data_Json = file_get_contents($Data_URL);
$Data = json_decode($Data_Json, true);
$Max_PAE = $Data["max_pae"];
$Data_PAE = $Data["pae"];
$Title = pathinfo($Data_URL)["filename"];
$Data_Length = count($Data_PAE);
?>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="/assets/js/highcharts/highcharts.js"></script>
    <script src="/assets/js/highcharts/exporting.js"></script>
    <script src="/assets/js/highcharts/data.js"></script>
    <script src="/assets/js/highcharts/heatmap.js"></script>
    <script src="/assets/js/highcharts/boost.js"></script>
    <script src="/assets/js/highcharts/boost-canv.js"></script>
    <script src="/assets/js/highcharts/accessibility.js"></script>
</head>

<body>
    <div id="container" style="height: 400px; max-width: 400px; margin: 0 auto"></div>
    <pre id="csv" style="display: none">Residue_x, Residue_y, PAE
<?php
for ($Residue_x = 0; $Residue_x < $Data_Length; $Residue_x++) {
    for ($Residue_y = 0; $Residue_y < $Data_Length; $Residue_y++) {
        echo $Residue_x . ',' . $Residue_y . ',' . $Data_PAE[$Residue_x][$Residue_y] . "\n";
    }
}
?></pre>
    <script>
        Highcharts.chart('container', {
            data: {
                csv: document.getElementById('csv').innerHTML
            },
            chart: {
                type: 'heatmap',
                inverted: true
            },
            boost: {
                useGPUTranslations: true
            },
            title: {
                text: '<?php echo $Title; ?>',
                align: 'left'
            },
            xAxis: {
                min: 0,
                max: <?php echo $Data_Length; ?>
            },
            yAxis: {
                title: {
                    text: null
                },
                min: 0,
                max: <?php echo $Data_Length; ?>,
                showLastLabel: false
            },
            colorAxis: {
                stops: [
                    [0, '#1F4E79'],
                    [1, '#DEEBF7']
                ],
                min: 0,
                max: <?php echo $Max_PAE; ?>,
                showLastLabel: false
            },
            series: [{
                boostThreshold: 100,
                borderWidth: 0,
                colsize: 1,
                tooltip: {
                    headerFormat: 'PAE<br/>',
                    pointFormat: '{point.x}-{point.y}: <b>{point.value}</b>'
                },
                turboThreshold: Number.MAX_VALUE
            }]
        });
    </script>
</body>

</html>