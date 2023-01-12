import re
import datetime
import logging
import shutil
import os
import time
import requests
import yaml
import abc
from jinja2 import Environment, FileSystemLoader

class GitHubApiCrawler(abc.ABC):

	__CONFIG_FILENAME = 'config.yml'

	def __init__(self, user_agent='nikolat/GitHubApiCrawler'):
		self._logger = self.__get_custom_logger()
		with open(self.__CONFIG_FILENAME, encoding='utf-8') as file:
			self._config = yaml.safe_load(file)
		self.__user_agent = user_agent

	def __get_custom_logger(self):
		custom_logger = logging.getLogger('custom_logger')
		custom_logger.setLevel(logging.DEBUG)
		handler = logging.StreamHandler()
		handler.setLevel(logging.DEBUG)
		custom_logger.addHandler(handler)
		handler_formatter = logging.Formatter(
			'%(asctime)s - [%(levelname)s]: %(message)s', datefmt='%Y-%m-%dT%H:%M:%SZ'
		)
		handler_formatter.converter = time.gmtime
		handler.setFormatter(handler_formatter)
		return custom_logger

	def _request_with_retry(self, url, payload, retry=True):
		logger = self._logger
		headers = {
			'Accept': 'application/vnd.github+json',
			'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}',
			'X-GitHub-Api-Version': '2022-11-28',
			'User-Agent': self.__user_agent
		}
		response = requests.get(url, params=payload, headers=headers)
		try:
			response.raise_for_status()
		except requests.RequestException as e:
			logger.warning(f'Status: {response.status_code}, URL: {url}')
			logger.debug(e.response.text)
			if retry:
				if 'Retry-After' in response.headers:
					wait = int(response.headers['Retry-After'])
				else:
					wait = 180
				logger.debug(f'Sleeping to retry after {wait} seconds.')
				time.sleep(wait)
				response = requests.get(url, params=payload, headers=headers)
				try:
					response.raise_for_status()
				except requests.RequestException as e:
					logger.warning(f'Status: {response.status_code}, URL: {url}')
					logger.debug(e.response.text)
					raise
				else:
					logger.debug(f'Status: {response.status_code}, URL: {url}')
		return response

	def search(self):
		config = self._config
		url = 'https://api.github.com/search/repositories'
		payload = {'q': config['search_query'], 'sort': 'updated'}
		responses = []
		response = self._request_with_retry(url, payload)
		responses.append(response)
		pattern = re.compile(r'<(.+?)>; rel="next"')
		result = pattern.search(response.headers['link']) if 'link' in response.headers else None
		while result:
			url = result.group(1)
			response = self._request_with_retry(url, None)
			responses.append(response)
			result = pattern.search(response.headers['link']) if 'link' in response.headers else None
		self._responses = responses
		return self

	@abc.abstractmethod
	def crawl(self):
		self._entries = []
		self._categories = []
		self._authors = []
		return self

	def export(self):
		config = self._config
		entries = self._entries
		categories = self._categories
		authors = self._authors
		env = Environment(loader=FileSystemLoader('./templates', encoding='utf8'), autoescape=True)
		# top page
		data = {
			'entries': entries,
			'config': config
		}
		for filename in ['index.html', 'rss2.xml']:
			template = env.get_template(filename)
			rendered = template.render(data)
			with open(f'docs/{filename}', 'w', encoding='utf-8') as f:
				f.write(rendered + '\n')
		# category
		for category in categories:
			shutil.rmtree(f'docs/{category}/', ignore_errors=True)
			os.mkdir(f'docs/{category}/')
			data = {
				'entries': [e for e in entries if e['category'] == category],
				'config': config
			}
			for filename in ['index.html', 'rss2.xml']:
				template = env.get_template(f'category/{filename}')
				rendered = template.render(data)
				with open(f'docs/{category}/{filename}', 'w', encoding='utf-8') as f:
					f.write(rendered + '\n')
		# author
		shutil.rmtree('docs/author/', ignore_errors=True)
		os.mkdir('docs/author/')
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
		# sitemap
		data = {
			'categories': categories,
			'authors': authors,
			'now': datetime.datetime.now().strftime('%Y-%m-%d'),
			'config': config
		}
		filename = 'sitemap.xml'
		template = env.get_template(filename)
		rendered = template.render(data)
		with open(f'docs/{filename}', 'w', encoding='utf-8') as f:
			f.write(rendered + '\n')
		return self
