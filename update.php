<?php
$dl = false;
$search_filename = 'repos.json';
if (file_exists('./repos/'. $search_filename)) {
    $t_file = filemtime('repos/'. $search_filename);
    $date_now = new DateTime('now');
    $date_now->modify('-60 minute');
    $t_now = $date_now->getTimestamp();
    if ($t_file < $t_now) {
        $dl = true; 
    }
}
else {
    $dl = true;
}
header('Content-type: text/javascript; charset=UTF-8');
if ($dl) {
    ob_start();
    include 'render.php';
    $html = ob_get_contents();
    ob_end_clean();
    file_put_contents(__DIR__. '/index.html', $html);
    echo 'console.log("index.html: update");';
}
else {
    echo 'console.log("index.html: keep");';
}
