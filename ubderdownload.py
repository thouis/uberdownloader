import urllib2
import time
import json
import sys
import os
import os.path
import traceback

def get_page_with_wait(url, wait=6):  # SGF throttling is 10/minute
    try:
        time.sleep(wait)
        response = urllib2.urlopen(url)
    except urllib2.HTTPError as e:
        if e.code == 429:  # too many requests
            print("Too many requests / minute, falling back to {} seconds between fetches.".format(int(1.5 * wait)))
            # exponential falloff
            return get_page_with_wait(url, wait=(1.5 * wait))
        raise
    else:
        # everything is fine
        return response.read()

def user_game_pages(user_id):
    url = "http://online-go.com/api/v1/players/{}/games/?format=json".format(user_id)
    while url is not None:
        data = json.loads(get_page_with_wait(url, 1))
        yield data
        url = data["next"]

def games_on_page(data):
    for r in data["results"]:
        yield r["id"]

if __name__ == "__main__":
    user_id = int(sys.argv[1])
    dest_dir = sys.argv[2]

    if not os.path.exists(dest_dir):
        os.mkdir(dest_dir)

    for s in user_game_pages(sys.argv[1]):
        for g in games_on_page(s):
            out_filename = os.path.join(dest_dir, "OGS_game_{}.sgf".format(g))
            if os.path.exists(out_filename):
                print("Skipping game {} because it has already been downloaded.".format(g))
                continue
            print("Downloading game {}...".format(g))
            sgf = get_page_with_wait("http://online-go.com/api/v1/games/{}/sgf".format(g))
            with open(out_filename, "w") as f:
                f.write(sgf)
