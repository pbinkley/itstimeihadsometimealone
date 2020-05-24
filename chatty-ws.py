#!/usr/bin/env python3

"""
Looks at your home timeline and tells you who tweets the most on it
"""

import csv
import sys
import time
import tweepy
import datetime
import asyncio
import websockets
import json

from utils import twitter
from collections import Counter

tweets = Counter()
users = Counter()
retweets = Counter()
quotes = Counter()
seen = set()

print("")
print("Following your home timeline tweet (🐦) quote (💬) retweet (🔁)")
print("Press CTRL-C to stop and output summary.\n")

start = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

async def server(websocket, path):
    while True:
        try:
            if len(seen) > 0:
                print("getting slice")
                slice = twitter.home_timeline(count=200, since_id=max(seen))
            else:
                print("getting first slice")
                slice = tweepy.Cursor(twitter.home_timeline, count=200).items(800)
            print("have slice")
            slice_count = 0
            for status in slice:
                print("processing tweet")
                slice_count += 1
                if status.id in seen:
                    return

                seen.add(status.id)
                user = status.user.screen_name
                users[user] += 1

                if hasattr(status, "quoted_status"): 
                    quotes[user] += 1
                    type = "💬"
                elif hasattr(status, "retweeted_status"):
                    retweets[user] += 1
                    type = "🔁"
                else:
                    tweets[user] += 1
                    type = "🐦"
                message = {
                    "type": type,
                    "id": status.id_str,
                    "user": user,
                    "text": status.text
                }
                print("Sending " + user + ": " + status.id_str)
                await websocket.send(json.dumps(message))
            print("Tweets received: " + str(slice_count))
            time.sleep(61)
        except tweepy.error.RateLimitError as e:
            print("sleeping", e)
            time.sleep(15 * 60)
        except tweepy.error.TweepError as e:
            print("caught Twitter API error sleeping")
            print(e.reason)
            time.sleep(60)
        except KeyboardInterrupt:
            break

start_server = websockets.serve(server, "127.0.0.1", 5678)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()

end = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
filename = "chatty-{}-{}.csv".format(start, end)
cols = ["User", "Quotes", "Tweets", "Retweets", "Total"]

print("\n\n")
print("| {:20s} | {:6s} | {:6s} | {:6s} | {:6s} |".format(*cols))
print("| -------------------- | ------ | ------ | ------ | ------ |")

with open(filename, "w") as fh:
    out = csv.writer(fh)
    out.writerow(["user", "quotes", "retweets", "tweets", "total"])
    for user, total in users.most_common():
        row = [
            user,
            quotes.get(user, 0),
            retweets.get(user, 0),
            tweets.get(user, 0),
            total
        ]
        print("| {:20s} | {:6n} | {:6n} | {:6n} | {:6n} |".format(*row))
        out.writerow(row)

print("\n")
print("full results written to {}".format(filename))
