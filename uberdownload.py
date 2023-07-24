from __future__ import unicode_literals

try:
    from urllib2 import urlopen
    from urllib2 import HTTPError, URLError
except ImportError:
    from urllib.request import urlopen
    from urllib.error import HTTPError, URLError

import time
import json
import sys
import os
import os.path

from loguru import logger


def get_page_with_wait(url, wait=6, max_retries=1, current_retry_count=0):  # SGF throttling is 10/minute
    if wait < 0.01:
        wait = 0.01

    try:
        time.sleep(wait)
        response = urlopen(url)
    except HTTPError as e:
        if e.code == 429:  # too many requests
            print("Too many requests / minute, falling back to {} seconds between fetches.".format(int(1.5 * wait)))
            # exponential falloff
            return get_page_with_wait(url, wait=(1.5 * wait))
        # raise            #Commented to allow script to continue
        if e.code == 403:
            return False
    except URLError as e:
        # sometimes DNS or the network temporarily falls over, and will come back if we try again
        if current_retry_count < max_retries:
            return get_page_with_wait(url, 5,
                                      current_retry_count=current_retry_count + 1)  # Wait 5 seconds between retries
        print("Can't fetch '{}'.  Check your network connection.".format(url))
        # raise            #Commented to allow script to continue
    else:
        return response.read()


def results(url):
    while url is not None:
        data = json.loads(get_page_with_wait(url, 0).decode('utf-8'))
        for _ in data["results"]:
            yield _
        url = data["next"]


def user_games(user_id):
    url = "https://online-go.com/api/v1/players/{}/games/?format=json".format(user_id)
    for _ in results(url):
        yield _["id"]


def user_reviews(user_id):
    return
    url = "https://online-go.com/api/v1/reviews/?owner__id={}&format=json".format(user_id)
    for r in results(url):
        yield r["id"], r["game"]["id"]


def reviews_for_game(game_id):
    return
    url = "https://online-go.com/api/v1/games/{}/reviews?format=json".format(game_id)
    for r in results(url):
        yield r["id"]


def save_sgf(out_filename, SGF_URL, name):
    if os.path.exists(out_filename):
        print("Skipping {} because it has already been downloaded.".format(name))
    else:
        print("Downloading {}...".format(name))
        sgf = get_page_with_wait(SGF_URL)
        if not sgf:
            print("Skipping {} because it encountered an error.".format(name))
        else:
            with open(out_filename, "wb") as f:
                f.write(sgf)


if __name__ == "__main__":
    user_id = int(sys.argv[1])
    dest_dir = sys.argv[2]

    if not os.path.exists(dest_dir):
        os.mkdir(dest_dir)

    for g in user_games(sys.argv[1]):
        save_sgf(os.path.join(dest_dir, "OGS_game_{}.sgf".format(g)),
                 "https://online-go.com/api/v1/games/{}/sgf".format(g),
                 "game {}".format(g))
        for r in reviews_for_game(g):
            save_sgf(os.path.join(dest_dir, "OGS_game_{}_review_{}.sgf".format(g, r)),
                     "https://online-go.com/api/v1/reviews/{}/sgf".format(g),
                     "review {} of game {}".format(r, g))

    for r, g in user_reviews(sys.argv[1]):
        save_sgf(os.path.join(dest_dir, "OGS_game_{}_review_{}.sgf".format(g, r)),
                 "https://online-go.com/api/v1/reviews/{}/sgf".format(g),
                 "review {} of game {}".format(r, g))
