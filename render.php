<?php
date_default_timezone_set('Asia/Tokyo');
if (!file_exists('./repos/')) {
    mkdir('./repos');
}
if (!file_exists('./readme/')) {
    mkdir('./readme');
}
$dl = true;
$max = 30;
$search_key = 'sosiremi';
$search_url = 'https://api.github.com/search/repositories?q=topic:'. $search_key. '&sort=updated';
$search_filename = 'repos.json';
if ($dl) {
    download_file($search_url, 'repos/'. $search_filename);
}
$json = file_get_contents(__DIR__. '/repos/'. $search_filename);
if ($json === false) {
    throw new \RuntimeException('file not found.');
}
$data_repos = json_decode($json, true);
$n = $data_repos['total_count'];
if ($n > $max) {
    $n = $max;
}
$repos = [];
$c = 0;
for ($i = 0; $i < $n; $i++) {
    $item = $data_repos['items'][$i];
    if (!isset($item['topics'])) {
        continue;
    }
    $topics = $item['topics'];
    $type = '';
    if (in_array('ukagaka-ghost', $topics)) {
        $type = 'ghost';
    }
    elseif (in_array('ukagaka-shell', $topics)) {
        $type = 'shell';
    }
    elseif (in_array('ukagaka-balloon', $topics)) {
        $type = 'balloon';
    }
    elseif (in_array('ukagaka-plugin', $topics)) {
        $type = 'plugin';
    }
    else {
        continue;
    }
    $latest_filename = str_replace('/', '_', $item['full_name']). '.json';
    $latest_url = str_replace('{/id}', '/latest', $item['releases_url']);
    if ($dl) {
        download_file($latest_url, 'repos/'. $latest_filename);
    }
    $json = file_get_contents(__DIR__. '/repos/'. $latest_filename);
    if ($json === false) {
        throw new \RuntimeException('file not found.');
    }
    $data_latest = json_decode($json, true);
    if (!isset($data_latest['assets'])) {
        continue;
    }
    $assets = $data_latest['assets'];
    for ($j = 0; $j < count($assets); $j++) {
        if ($assets[$j]['content_type'] != 'application/x-nar') {
            continue;
        }
        $readme_filename = str_replace('/', '_', $item['full_name']). '.txt';
        $readme_url = 'https://raw.githubusercontent.com/'. $item['full_name']. '/'. $item['default_branch']. '/readme.txt';
        if ($dl) {
            download_file($readme_url, 'readme/'. $readme_filename);
        }
        $readme = file_get_contents(__DIR__. '/readme/'. $readme_filename);
        if ($readme === false) {
            throw new \RuntimeException('file not found.');
        }
        $repo = [
            'id' => str_replace('/', '_', $item['full_name']),
            'title' => $item['name'],
            'category' => $type,
            'author' => $item['owner']['login'],
            'html_url' => $item['html_url'],
            'created_at_time' => $data_latest['assets'][$j]['created_at'],
            'created_at_str' => date("Y-m-d H:i:s", strtotime($data_latest['assets'][$j]['created_at'])),
            'updated_at_time' => $data_latest['assets'][$j]['updated_at'],
            'updated_at_str' => date("Y-m-d H:i:s", strtotime($data_latest['assets'][$j]['updated_at'])),
            'browser_download_url' => $data_latest['assets'][$j]['browser_download_url'],
            'filesize' => round($data_latest['assets'][$j]['size'] / 1024, 1),
            'readme' => $readme
        ];
        $repos[$c] = $repo;
        $c++;
        break;
    }
}
function download_file($url, $filename)
{
    $ch = curl_init($url);
    $fp = fopen($filename, 'w');
    curl_setopt($ch, CURLOPT_FILE, $fp);
    curl_setopt($ch, CURLOPT_HEADER, 0);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/1.0 (Win3.1)');
    curl_exec($ch);
    if(curl_error($ch)) {
        fwrite($fp, curl_error($ch));
    }
    curl_close($ch);
    fclose($fp);
}
function s($s)
{
    return htmlspecialchars($s);
}
?><!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width" />
<title>偽SoSiReMi</title>
<link rel="stylesheet" href="./media/css/common.css" media="screen and (min-device-width: 481px)" />
<link rel="stylesheet" href="./media/css/smartphone.css" media="only screen and (max-device-width: 480px)" />
<link rel="help" href="./about.html" />
<?php for ($i = 0; $i < count($repos); $i++) { ?>
<link rel="alternate" type="application/x-nar" title="<?php echo s($repos[$i]['title']); ?>" href="<?php echo s($repos[$i]['browser_download_url']); ?>" />
<?php } ?>
<script src="./update.php" defer="defer"></script>
</head>
<body>
	<header id="header">
		<div id="title-area">
			<h1 id="title"><a href="./">偽SoSiReMi</a></h1>
		</div>
		<nav id="site-navigation-area">
			<h1>navigation</h1>
			<ul>
				<li class="about"><a href="./about.html" rel="help">このサイトについて</a></li>
			</ul>
		</nav>
	</header>
	<section id="content" class="hfeed">
		<h1 class="entries-caption">entries</h1>
<?php for ($i = 0; $i < count($repos); $i++) { ?>
		<article id="<?php echo s($repos[$i]['id']); ?>" class="hentry autopagerize_page_element">
    		<h1 class="entry"><?php echo s($repos[$i]['id']); ?></h1>
			<div class="profile">
				<h1 class="entry-title"><a href="<?php echo s($repos[$i]['html_url']); ?>" rel="bookmark"><?php echo s($repos[$i]['title']); ?></a></h1>
				<dl>
					<dt class="category">カテゴリ</dt>
					<dd class="category"><?php echo s($repos[$i]['category']); ?></dd>
					<dt class="author">作者名</dt>
					<dd class="author"><?php echo s($repos[$i]['author']); ?></dd>
					<dt class="created">投稿日時</dt>
					<dd class="created"><time datetime="<?php echo s($repos[$i]['created_at_time']); ?>"><?php echo s($repos[$i]['created_at_str']); ?></time></dd>
					<dt class="updated">更新日時</dt>
					<dd class="updated"><time datetime="<?php echo s($repos[$i]['updated_at_time']); ?>"><?php echo s($repos[$i]['updated_at_str']); ?></time></dd>
				</dl>
				<p class="download"><a href="<?php echo s($repos[$i]['browser_download_url']); ?>" title="<?php echo s($repos[$i]['browser_download_url']); ?>" rel="nofollow" data-filesize="<?php echo s($repos[$i]['filesize']); ?>">download</a></p>
				<p class="download install"><a href="<?php echo s('x-ukagaka-link:type=install&url='. urlencode($repos[$i]['browser_download_url'])); ?>" title="<?php echo s($repos[$i]['browser_download_url']); ?>" rel="nofollow">install</a></p>
			</div>
			<aside class="readme">
				<h1>readme</h1>
<pre>
<?php echo s($repos[$i]['readme']); ?>
</pre>
			</aside>
		</article>
<?php } ?>
	</section>
	<footer id="footer">
		<p id="copyright"><small>Copyright &#169; 2022 <a href="./">偽SoSiReMi</a></small></p>
	</footer>
</body>
</html>
