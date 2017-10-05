import json
import logging
import re

import requests
import sys
from bs4 import BeautifulSoup
from bs4 import Comment
from docopt import docopt

l = logging.getLogger(__name__)

HELP = """ 
Usage: chia-anime-downloader.py search <keyword> [--verbose]
       chia-anime-downloader.py download <link> [--verbose]
Options:
    --verbose       Print debug logging
"""

# Download by search keyword or link

def download_by_keyword(keyword=None):
    '''
    Function called when user selects (1), meaning they are only providing the name of the
    anime. Calls private functions to gather request data, parse and normalize it, and
    offer storage services.
    '''
    if not keyword:
        anime_name = input("Enter the name of anime you wish to download from chia-anime.tv: ")
    else:
        anime_name = keyword
    search_url = "http://www.chia-anime.tv/search/" + anime_name  # Visiting search page for relevant animes
    searchpage = requests.get(search_url)  # fetch response object for search page
    search_soup = BeautifulSoup((searchpage).text, "lxml")  # parse the response object as HTML

    # Display search results
    search_counter = 1
    anime_page_links = []  # An array to hold anime page links from searched results
    print("Search results:")

    for x in search_soup.find_all(class_="title"):
        print(search_counter, x.a.text)
        anime_page_links.append(x.a['href'])
        search_counter += 1

    # No search results for the given keyword
    if len(anime_page_links) == 0:
        print("Nothing Found")
        exit(0)

        # Select from search results
    search_index = int(input("Enter what you think is appropriate: "))
    anime_page_link = anime_page_links[search_index - 1]

    anime_episode_links = _get_episode_links(anime_page_link)

    episode_start, episode_end = _get_episode_range(anime_episode_links)

    episode_quality = _get_episode_quality()

    episode_download = _get_animepremium_links(anime_episode_links, episode_start, episode_end, episode_quality)

    _store_results(anime_name, episode_download)


def download_by_link(link=None):
    '''
    Function called when user selects (2), meaning they are providing a link to the anime
    url page. Calls private functions to gather request data, parse and normalize it, and
    offer storage services.
    '''
    if not link:
        anime_page_link = input("Paste the link of the anime page:")
    else:
        anime_page_link = link

    anime_name = anime_page_link.split('/')[-2]

    anime_episode_links = _get_episode_links(anime_page_link)

    episode_start, episode_end = _get_episode_range(anime_episode_links)

    episode_quality = _get_episode_quality()

    episode_download = _get_animepremium_links(anime_episode_links, episode_start, episode_end, episode_quality)

    _store_results(anime_name, episode_download)


def _store_results(anime_name, episode_download):
    '''
    Private function that stores the gathered download links
    '''
    optype = int(input('Save links for later use (1) or download them now (2):'))
    if optype == 1:
        with open(anime_name + ".txt", 'w') as f:
            for x in episode_download:
                f.write('{} \n\n'.format(x))


def _get_animepremium_links(anime_episode_links, start, end, episode_quality):
    '''
    Private function that gets the animepremium download links
    '''
    episode_download = []
    episode_num = start
    alt_server_link_pattern = re.compile("\$\(\"#downloader\"\).load\('(.*)'\)")
    scraper = cfscrape.create_scraper()
    for episode_page in anime_episode_links[start - 1:end]:
        episode_page_soup = BeautifulSoup(scraper.get(episode_page,
                                                                 headers={"User-Agent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.96 Safari/537.36',
                                                                          "Referer": "http://chia-anime.tv"}).text, "lxml")
        for x in episode_page_soup.find_all(id="download"):
            animepremium_page_soup = BeautifulSoup(scraper.get(x['href'],
                                                                 headers={"User-Agent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36',
                                                                          "Referer": episode_page}).text, "lxml")
            available_qualities = {}
            for y in animepremium_page_soup.find_all(rel="nofollow"):
                if y.text in ['360p', '480p', '720p', '1080p']:
                    available_qualities.update({int(y.text[:-1]): y['href']})
            for script in animepremium_page_soup.find_all("script"):
                if "$(\"#downloader\")" in script.text:
                    alternate_server_link = re.findall(alt_server_link_pattern, script.text)[0]
            alternate_server_soup = BeautifulSoup(scraper.get(alternate_server_link,
                                                                 headers={"User-Agent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36',
                                                                          "Referer": x['href']}).text, "lxml")
            alternate_server_link_soup = BeautifulSoup(
                ''.join(alternate_server_soup.find_all(string=lambda text:isinstance(text,Comment))), "lxml")
            for i in alternate_server_link_soup.find_all(rel="nofollow"):
                available_qualities.update({int(i.text[:-1]): i['href']})
            _ep_quality = int(episode_quality[:-1])
            for quality in reversed(sorted(available_qualities)): # Cause we want the next-highest quality
                if _ep_quality >= quality:
                    episode_download.append(available_qualities[quality])
                    if _ep_quality > quality:
                        print("WARNING: %dp quality not available for episode #%d. Using next-highest quality: %dp."
                              % (_ep_quality, episode_num, quality))
                    break
        episode_num += 1
    return episode_download


def _get_episode_links(anime_page_link):
    '''
    Private function that aggregates episode links
    '''
    anime_name = anime_page_link.split('/')[-2]  # get second last item
    anime_episode_links = []  # list to store episode links scraped from anime page
    animepagesoup = BeautifulSoup((requests.get(anime_page_link)).text, "lxml")
    for x in animepagesoup.find_all('h3'):
        anime_episode_links.append(x.a['href'])
    anime_episode_links.reverse()  # Reverse the links array since chia-anime stores links in reverse order
    return anime_episode_links


def _get_episode_range(anime_episode_links):
    '''
    Private function that gets the range of episodes
    '''
    while (True):
        episode_start = int(input('Entering starting episode:'))
        episode_end = int(input('Enter ending episode:'))
        if (episode_start > 0 and episode_start < len(anime_episode_links) and episode_end >= 1 and episode_end <= len(
                anime_episode_links) and episode_start <= episode_end):
            break
        else:
            print('Invalid episode selection, try again.')
    return episode_start, episode_end


def _get_episode_quality():
    '''
    Private function that gets the episode quality based on user input
    '''
    while (True):
        quality = input('Enter the quality of the episode (360p, 480p, 720p, 1080p):')
        if quality in ['360p', '480p', '720p', '1080p']:
            break
        else:
            print('Invalid quality input, try again.')
    return quality


def main():
    # Download by link or by name ?
    choice = int(input("Enter (1) to search anime or (2) to download from link: "))

    if choice == 1:
        download_by_keyword()
    else:
        download_by_link()


if __name__ == '__main__':
    opts = docopt(HELP, argv=sys.argv[1:])
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
                        level=logging.DEBUG if opts["--verbose"] else logging.ERROR)
    l.debug("Arguments %s", json.dumps(opts))
    if opts["search"] and len(opts["<keyword>"]) > 0:
        # User wants to search and provide a keyword
        download_by_keyword(keyword=opts["<keyword>"])
    elif opts["download"] and len(opts["<link>"]) > 0:
        # User provide a link to download
        download_by_link(link=opts["<link>"])
    else:
        main()
