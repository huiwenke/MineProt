<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MineProt</title>
    <link rel="shortcut icon" type="image/png" href="/assets/img/logo.png">
    <link rel="stylesheet" type="text/css" href="/assets/css/style.css">
</head>

<body>
    <header style="position: relative !important;">
        <div id="logo">
            <img src="/assets/img/logo.png" height="32" width="32" class="logo" />
        </div>

        <div class="middle_section" id="middle_section">
            <nav>
                <strong>MineProt</strong>
            </nav>
        </div>

        <div class="parent">
            <div style="display: block;">
                <a class="nav_link" href="import.php">Import</a>
            </div>
        </div>

        <div class="parent">
            <div style="display: block;">
                <a class="nav_link" href="download.php">Download</a>
            </div>
        </div>

    </header>

    <main style="min-height: 100vh;">
        <section id="aside" class="aside" style="display: inline-flex;">
            <div class="child">
                <form action="search.php">
                    <div style="margin-bottom: 16px; margin-top: 8px;">
                        <label class="wrapper">
                            <input class="form-control-header" placeholder="Search your proteins...">
                        </label>
                    </div>
                    <div style="margin-bottom: 16px; margin-top: 8px;"></div>
                    <h2 class="h2_aside">
                        Protein Repositories
                    </h2>
                    <div style="margin-bottom: 16px; margin-top: 8px;"></div>
                    <ul>
                        <li>
                            <div class="list-item-div">
                                <input type="checkbox" id="cbox1" value="first_checkbox" class="a-item-div">
                                <label for="cbox1">
                                    <font color="white">Repo 1</font>
                                </label>
                            </div>
                        </li>
                    </ul>
                    <ul>
                        <li>
                            <div class="list-item-div">
                                <input type="checkbox" id="cbox1" value="first_checkbox" class="a-item-div">
                                <label for="cbox1">
                                    <font color="white">Repo 1</font>
                                </label>
                            </div>
                        </li>
                    </ul>
                    <ul>
                        <li>
                            <div class="list-item-div">
                                <input type="checkbox" id="cbox1" value="first_checkbox" class="a-item-div">
                                <label for="cbox1">
                                    <font color="white">Repo 1</font>
                                </label>
                            </div>
                        </li>
                    </ul>
                    <div style="margin-bottom: 16px; margin-top: 8px;"></div>
                    <button class="btn" type="submit">Submit</button>
                </form>
            </div>
        </section>

        <section class="main">
            <div style="display: block; width: 100%;">
                <h2 class="main_h2">All activity</h2>
                <div class="card">
                    <span style="margin-right: 8px;">
                        <a href="#" style="display:inline-block;">
                            <img class="avatar" src="./img/person.jfif" width="32" height="32" alt="@XZANATOL">
                        </a>
                    </span>
                    <a class="card-link" href="#">User X</a>
                    <span style="color:#c9d1d9;">&nbsp;started following&nbsp;</span>
                    <a class="card-link" href="#">User Y</a>
                    <div class="card-inner-div">
                        <div style="display: flex;">
                            <a href="#" style="display:inline-block;">
                                <img class="avatar" src="./img/person.jfif" width="40" height="40" alt="@XZANATOL">
                            </a>
                            <div style="margin-left: 16px;">
                                <a class="card-link user-properties-link" href="#">User Y</a>
                                <div style="color:#c9d1d9; margin-top: 7px;">User Status: software engineer by day, software engineer by night.</div>
                                <br>
                                <span style="color: #8b949e;">
                                    <a href="#" style="margin-right:16px; color: inherit;" class="user-properties-link">x repositories</a>
                                    <a href="#" style="margin-right:16px; color: inherit;" class="user-properties-link">y followers</a>
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </main>
</body>

</html>