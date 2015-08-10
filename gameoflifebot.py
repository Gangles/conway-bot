#!/usr/bin/python

import config
import datetime
import os
import re
import sys
import time
from twython import Twython

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from gol.conway import conway
import numpy as np

from images2gif import writeGif
from PIL import Image

def simulateLife(colour):
    # set up the board
    m,n = 50,100
    A = np.random.random(m*n).reshape((m, n))
    A = np.multiply(A, 1.0 + np.random.random_sample() * 0.5).round()
    A = conway(A)
    
    # plot each frame
    fig = plt.figure(frameon=False)
    fig.set_size_inches(5, 2.5)
    ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])
    ax.set_axis_off()
    fig.add_axes(ax)
    img_plot = plt.imshow(A, interpolation="nearest", cmap = colour, vmin = 0, vmax = 1)
    
    # simulate 100 generations
    for i in xrange(100):
        print "Simulating generation " + str(i).zfill(3)
        B = conway(A)
        img_plot.set_data(B)
        extent = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        plt.savefig('./tmp/conway_' + str(i).zfill(3) + '.png', dpi=100, bbox_inches=extent, pad_inches=0)
        if np.array_equal(A, B): break
        A = B

def makeGIF():
    # assemble the GIF
    print "Assembling GIF..."
    file_names = sorted((fn for fn in os.listdir('./tmp/') if fn.endswith('.png')))
    images = [Image.open('./tmp/' + fn) for fn in file_names]
    writeGif('gameoflife.gif', images, duration=0.1)

def cleanupFiles():
    # delete any leftover images
    for file in os.listdir('./tmp/'):
        file_path = os.path.join('./tmp/', file)
        if os.path.isfile(file_path):
            os.unlink(file_path)

def connectTwitter():
    # connect to twitter API
    return Twython(config.twitter_key, config.twitter_secret, config.access_token, config.access_secret)

def getTweetNumber(twitter):
    # increment the last numbered tweet
    number = 0
    timeline = twitter.get_user_timeline(screen_name = config.bot_name)
    if len(timeline) > 0:
        match = re.search(r'^\d+', timeline[0]['text'])
        if match:
            number = int(match.group())
    return number + 1

def getGifColour(number):
    # use a sequential colour for the GIF
    colours = [plt.cm.gray, plt.cm.summer, plt.cm.spring, plt.cm.autumn, plt.cm.winter,
                plt.cm.cool, plt.cm.ocean, plt.cm.rainbow, plt.cm.seismic, plt.cm.BrBG]
    return colours[(number - 1) % len(colours)]

def postTweet(twitter, number):
    # post the tweet with the gif
    to_tweet = str(number).zfill(6)
    gif = open('gameoflife.gif', 'rb')
    assert os.fstat(gif.fileno()).st_size <= 3145728, "GIF file too large"
    twitter.update_status_with_media(status=to_tweet, media=gif)
    print "Posted tweet with GIF #" + to_tweet

def timeToWait():
    # tweet every 12 hours
    now = datetime.datetime.now()
    wait = 60 - now.second
    wait += (59 - now.minute) * 60
    wait += (11 - (now.hour % 12)) * 60 * 60;
    return wait

if __name__ == "__main__":
    # heroku scheduler runs every 10 minutes
    wait = timeToWait()
    print "Wait " + str(wait) + " seconds for next tweet"
    if wait > 10 * 60:
        sys.exit(0)

    try:
        # make sure the temp folder exists
        if not os.path.exists('./tmp/'):
            os.mkdir('./tmp/')
    
        # run the simulation and make the GIF
        cleanupFiles()
        twitter = connectTwitter()
        number = getTweetNumber(twitter)
        colour = getGifColour(number)
        simulateLife(colour)
        makeGIF()

        # wait until the right time, then post
        time.sleep(min(wait, timeToWait()))
        postTweet(twitter, number)
        sys.exit(0) # success!
    except SystemExit as e:
        # working as intended, exit normally
        sys.exit(e)
    except:
        print "Error:", sys.exc_info()[0]
        sys.exit(1)
    
