import crawler
import datetime
import zoneinfo
import requests
import urllib.parse
from decimal import Decimal

class GitHubNarStation(crawler.GitHubApiCrawler):

	__ALLOWED_CATEGORIES = ['ghost', 'shell', 'balloon', 'plugin', 'supplement']

	def __init__(self):
		super().__init__('nikolat/GitHubNarStation')

	def crawl(self):
		jst = zoneinfo.ZoneInfo('Asia/Tokyo')
		logger = self._logger
		config = self._config
		responses = self._responses
		entries = []
		categories = []
		authors = []
		for response in responses:
			for item in response.json()['items']:
				types = [t.replace('ukagaka-', '') for t in item['topics'] if 'ukagaka-' in t]
				if len(types) == 0:
					logger.debug(f'ukagaka-* topic is not found in {item["full_name"]}')
					continue
				types = [t for t in types if t in self.__ALLOWED_CATEGORIES]
				if len(types) == 0:
					logger.debug(f'ukagaka-* topic is not allowed in {item["full_name"]}')
					continue
				category = types[0]
				if item['full_name'] in config['redirect'] and 'nar' in config['redirect'][item['full_name']]:
					logger.debug(f'releases_url is redirected form {item["full_name"]} to {config["redirect"][item["full_name"]]["nar"]}')
					item['releases_url'] = item['releases_url'].replace(item['full_name'], config['redirect'][item['full_name']]['nar'])
				latest_url = item['releases_url'].replace('{/id}', '/latest')
				response = self._request_with_retry(latest_url, None)
				l_item = response.json()
				if 'assets' not in l_item:
					logger.debug(f'assets are not found in {item["full_name"]}')
					continue
				assets = [a for a in l_item['assets'] if a['content_type'] in ['application/x-nar', 'application/zip', 'application/x-zip-compressed', 'application/octet-stream']]
				if len(assets) == 0:
					logger.debug(f'NAR file is not found in {item["full_name"]}')
					logger.debug(f'content_type: {l_item["assets"][0]["content_type"]}')
					continue
				asset = assets[0]
				dt_created = datetime.datetime.strptime(asset['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).astimezone(tz=jst)
				dt_updated = datetime.datetime.strptime(asset['updated_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).astimezone(tz=jst)
				if item['full_name'] in config['redirect'] and 'readme' in config['redirect'][item['full_name']]:
					logger.debug(f'README file is redirected form {item["full_name"]} to {config["redirect"][item["full_name"]]["readme"]}')
					readme_url = config['redirect'][item['full_name']]['readme']
				else:
					readme_url = f'https://raw.githubusercontent.com/{item["full_name"]}/{item["default_branch"]}/readme.txt'
				response = requests.get(readme_url)
				try:
					response.raise_for_status()
					response.encoding = response.apparent_encoding
					readme = response.text
				except requests.HTTPError as e:
					url = f'https://api.github.com/repos/{item["full_name"]}/readme'
					response = self._request_with_retry(url, None, retry=False)
					r_item = response.json()
					if 'download_url' in r_item:
						readme_url = r_item['download_url']
						response = requests.get(readme_url)
						response.encoding = response.apparent_encoding
						readme = response.text
						logger.debug(f'README is found at {readme_url} in {item["full_name"]}')
					else:
						readme = 'readme.txt not found'
						logger.debug(f'README is not found in {item["full_name"]}')
				entry = {
					'id': item['full_name'].replace('/', '_'),
					'title': item['name'],
					'category': category,
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
				if category not in categories:
					categories.append(category)
				if item['owner']['login'] not in authors:
					authors.append(item['owner']['login'])
		self._entries = entries
		self._categories = categories
		self._authors = authors
		return self

if __name__ == '__main__':
	g = GitHubNarStation()
	g.search().crawl().export()
