import re
import datetime
import shutil
import os
import zoneinfo
import requests
import yaml
import urllib.parse
from decimal import Decimal
from jinja2 import Environment, FileSystemLoader

if __name__ == '__main__':
	jst = zoneinfo.ZoneInfo('Asia/Tokyo')
	config_filename = 'config.yml'
	with open(config_filename, encoding='utf-8') as file:
		config = yaml.safe_load(file)
	url = 'https://api.github.com/search/repositories'
	headers = {
		'Accept': 'application/vnd.github+json',
		'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}',
		'X-GitHub-Api-Version': '2022-11-28',
		'User-Agent': 'nikolat/github-nar-station'
	}
	payload = {'q': config['search_query'], 'sort': 'updated'}
	responses = []
	response = requests.get(url, params=payload, headers=headers)
	response.raise_for_status()
	responses.append(response)
	pattern = re.compile(r'<(.+?)>; rel="next"')
	result = pattern.search(response.headers['link']) if 'link' in response.headers else None
	while result:
		url = result.group(1)
		response = requests.get(url, headers=headers)
		response.raise_for_status()
		responses.append(response)
		result = pattern.search(response.headers['link']) if 'link' in response.headers else None
	now = datetime.datetime.now()
	entries = []
	authors = []
	for response in responses:
		for item in response.json()['items']:
			types = [t.replace('ukagaka-', '') for t in item['topics'] if 'ukagaka-' in t]
			types = [t for t in types if t in ['ghost', 'shell', 'balloon', 'plugin', 'supplement']]
			if len(types) == 0:
				continue
			if item['full_name'] in config['redirect'] and 'nar' in config['redirect'][item['full_name']]:
				item['releases_url'] = item['releases_url'].replace(item['full_name'], config['redirect'][item['full_name']]['nar'])
			latest_url = item['releases_url'].replace('{/id}', '/latest')
			response = requests.get(latest_url, headers=headers)
			l_item = response.json()
			if 'assets' not in l_item:
				continue
			assets = [a for a in l_item['assets'] if a['content_type'] in ['application/x-nar', 'application/zip', 'application/x-zip-compressed', 'application/octet-stream']]
			if len(assets) == 0:
				continue
			asset = assets[0]
			dt_created = datetime.datetime.strptime(asset['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).astimezone(tz=jst)
			dt_updated = datetime.datetime.strptime(asset['updated_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).astimezone(tz=jst)
			if item['full_name'] in config['redirect'] and 'readme' in config['redirect'][item['full_name']]:
				readme_url = config['redirect'][item['full_name']]['readme']
			else:
				readme_url = f'https://raw.githubusercontent.com/{item["full_name"]}/{item["default_branch"]}/readme.txt'
			response = requests.get(readme_url)
			try:
				response.raise_for_status()
				response.encoding = response.apparent_encoding
				readme = response.text
			except requests.HTTPError as e:
				readme_url = None
				url = f'https://api.github.com/repos/{item["full_name"]}/readme'
				response = requests.get(url, headers=headers)
				if response.status_code == requests.codes.ok:
					r_item = response.json()
					if 'download_url' in r_item:
						readme_url = r_item['download_url']
				if readme_url:
					response = requests.get(readme_url)
					response.encoding = response.apparent_encoding
					readme = response.text
				else:
					readme = 'readme.txt not found'
			entry = {
				'id': item['full_name'].replace('/', '_'),
				'title': item['name'],
				'category': types[0],
				'author': item['owner']['login'],
				'html_url': item['html_url'],
				'content_type': asset['content_type'],
				'created_at_time': asset['created_at'],
				'created_at_str': dt_created.strftime('%Y-%m-%d %H:%M:%S'),
				'updated_at_time': asset['updated_at'],
				'updated_at_str': dt_updated.strftime('%Y-%m-%d %H:%M:%S'),
				'updated_at_rss2': dt_updated.strftime('%a, %d %b %Y %H:%M:%S %z'),
				'browser_download_url': asset['browser_download_url'],
				'install_uri': 'x-ukagaka-link:type=install&url=' + urllib.parse.quote_plus(asset['browser_download_url']),
				'filesize': Decimal(asset['size'] / 1024).quantize(Decimal('0.1')),
				'download_count': asset['download_count'],
				'readme': readme
			}
			entries.append(entry)
			if item['owner']['login'] not in authors:
				authors.append(item['owner']['login'])
	env = Environment(loader=FileSystemLoader('./templates', encoding='utf8'), autoescape=True)
	data = {
		'entries': entries,
		'config': config
	}
	shutil.rmtree('docs/author/', ignore_errors=True)
	os.mkdir('docs/author/')
	for filename in ['index.html', 'rss2.xml']:
		template = env.get_template(filename)
		rendered = template.render(data)
		with open(f'docs/{filename}', 'w', encoding='utf-8') as f:
			f.write(rendered + '\n')
	data = {
		'authors': authors,
		'now': now.strftime('%Y-%m-%d'),
		'config': config
	}
	filename = 'sitemap.xml'
	template = env.get_template(filename)
	rendered = template.render(data)
	with open(f'docs/{filename}', 'w', encoding='utf-8') as f:
		f.write(rendered + '\n')
	for author in authors:
		os.mkdir(f'docs/author/{author}/')
		data = {
			'entries': [e for e in entries if e['author'] == author],
			'config': config
		}
		for filename in ['index.html', 'rss2.xml']:
			template = env.get_template(f'author/{filename}')
			rendered = template.render(data)
			with open(f'docs/author/{author}/{filename}', 'w', encoding='utf-8') as f:
				f.write(rendered + '\n')
