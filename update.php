<?php
ob_start();
include 'render.php';
$html = ob_get_contents();
ob_end_clean();
array_map('unlink', glob('repos/*.json'));
array_map('unlink', glob('readme/*.txt'));
file_put_contents(__DIR__. '/docs/index.html', $html);
