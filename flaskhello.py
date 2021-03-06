﻿import feedparser
import random
import json
import itertools
from random import shuffle
from bs4 import BeautifulSoup
import urllib3
import shutil
# import html
# import multiprocessing

from flask_mobility import Mobility
from flask import Flask, render_template, Markup, request
from flask_caching import Cache
from wtforms import Form, BooleanField, FormField, FieldList, StringField, IntegerField, validators, SelectField

http = urllib3.PoolManager()

g_app = Flask(__name__)
Mobility(g_app)
application = g_app

# from flask_table import Table, Col
#    <a target="_blank" href = "{{ link }}"><img src = "{{ image_url }}" style="max-height: 100px;"/>

EXPIRE_MINUTES = 60 * 10

#Expire things faster in debug mode
#if g_app.debug == True:
#    EXPIRE_MINUTES = 60
#    print ("In debug mode, so expires faster")

EXPIRE_HOURS = 3600
EXPIRE_DAY = 3600 * 6
EXPIRE_DAYS = 86400 * 10
EXPIRE_YEARS = 60 * 60 * 24 * 365 * 2

g_app.config['SEND_FILE_MAX_AGE_DEFAULT'] = EXPIRE_DAYS

site_urls = { "http://lxer.com/module/newswire/headlines.rss" : 
             ["http://keithcu.com/images/lxer.webp",
              "http://lxer.com/",
              EXPIRE_HOURS],
    
              "http://www.reddit.com/r/linux/.rss" : 
             ["http://keithcu.com/images/redditlogosmall.webp",
              "https://www.reddit.com/r/linux",
              EXPIRE_HOURS],

              "http://rss.slashdot.org/Slashdot/slashdotMain" : 
             ["http://keithcu.com/images/slashdotlogo.webp",
              "https://slashdot.org/",
              EXPIRE_HOURS],

              "http://lwn.net/headlines/newrss" :
             ["http://keithcu.com/images/barepenguin-70.webp",
              "https://lwn.net/",
              EXPIRE_DAY],

              "http://news.ycombinator.com/rss" :
             ["http://keithcu.com/images/hackernews.webp",
              "http://news.ycombinator.com/",
              EXPIRE_HOURS],

               "http://planet.debian.org/rss20.xml" :
             ["http://keithcu.com/images/Debian-OpenLogo.svg",
              "http://planet.debian.org/",
              EXPIRE_HOURS],

              "http://www.osnews.com/feed/" :
             ["http://keithcu.com/images/osnews-logo.webp",
              "http://www.osnews.com/",
              EXPIRE_HOURS],

              "http://www.geekwire.com/feed/" :
             ["http://keithcu.com/images/GeekWire.png",
              "http://www.geekwire.com/",
              EXPIRE_HOURS],

               "http://feeds.feedburner.com/linuxtoday/linux" :
             ["http://keithcu.com/images/linuxtd_logo.png",
              "http://www.linuxtoday.com/",
              EXPIRE_HOURS],

            }

 
class HelloCache(object):
    def __init__(self):
        global g_app
        self._cache = Cache(g_app, config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR' : '/tmp/flaskhello/', 'CACHE_DEFAULT_TIMEOUT' : EXPIRE_DAY })

    def Put(self, url, template, timeout = None):
        self._cache.set(url, template, timeout)
        
    def Get(self, url):
        template = self._cache.get(url)

        return template


def GrabImageTest(feedinfo):

    #Search for first image in first article of feed:
    feed = feedinfo[0]
    url = feed.link

    #url = "http://keithcu.com/wordpress/?p=3847"

    http_response = g_c.Get(url)

    #Try to grab the mobile page since it is easier to find the correct first image
    if http_response is None:
        headers_mobile = { 'User-Agent' : 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B137 Safari/601.1'}
        http_response = http.request("Get", url, headers=headers_mobile).data
        g_c.Put(url, http_response, timeout = EXPIRE_DAYS)

    soup = BeautifulSoup(http_response, features = "lxml")
    img = None
    for img in soup.findAll('img'):
        if 'gravatar' in img.attrs['src'] or 'themes' in img.attrs['src'] or 'qsstats' in img.attrs['src']:
            continue
        else:
            print (img)
            break

    #Can't find an image, so give up
    if img is None:
        return None

    img_url = img.attrs['src']

    names = img_url.split("/")
    print (names[-1])

    try:
        response = http.request("Get", img_url)
        filename = "/srv/http/images/" + names[-1]
        f = open(filename, "wb+")
        shutil.copyfileobj(response, f)
    except:
        return None

    return "http://keithcu.com/images/" + names[-1]


g_c = None
g_standard_order = list(site_urls.keys())
g_standard_order_s = str(g_standard_order)

@g_app.route('/')
def index():

    global g_c
    global g_app
    global g_standard_order
    global g_standard_order_s

    if g_c is None:
        g_c = HelloCache()

    page_order = request.cookies.get('RssUrls')
    if page_order is not None:
        page_order = json.loads(page_order)
    
    if page_order is None:
        page_order = g_standard_order

        # for key, value in site_urls.items():
        #     if value[0] != "http://keithcu.com/images/Custom.png":
        #         page_order.append(key)
    
    #There's a question as to whether it's worth trying to cache
    #all possible custom page layouts.
    #That could cause us to use at least 40,000 files with just
    #8 URL variants.
    #On my machine I can do 300 requests per second with no page cache
    #or 400 with a page cache. I'll just cache the "standard layout" page.

    page_order_s = str(page_order)

    suffix = ""
    if request.MOBILE:
        suffix = ":MOBILE"

    if page_order_s == g_standard_order_s:
        full_page = g_c.Get(page_order_s + suffix)
        if full_page is not None:
            return full_page
    
    result = [[], [], []]
    cur_col = 0
        
    for url in page_order:
        
        site_info = site_urls.get(url, None)

        if site_info is None:
            site_info = ["http://keithcu.com/images/Custom.png", url + "HTML", EXPIRE_HOURS]
            site_urls[url] = site_info

        logo_url, site_url, expire_time = site_info

        #First check for the templatized content stored with site URL
        template = g_c.Get(site_url)

        if template is None:
            jitter = random.randint(0, 60 * 5) #Add up to 5 minutes of jitter to spread out updates

            #Check for RSS content to save network fetch
            feedinfo = g_c.Get(url)
            if feedinfo is None:
                #Consider adding code to make sure only one process tries to fetch
                #at a time after expiration (considering multiple processes on a busy server)
                #Implement a two-stage process where first I check for the pid.
                #if it doesn't exist, create it. Then check again if it's me.
                #If it is, then fetch.
                #Otherwise, sleep for 50 ms and try again.
                #Some people will have pauses, but it should only be a small number
                #every hours or so.

                #An alternative way of caching is to never expire the HTML templates.
                #Just create a thread which sleeps for 10 seconds, and then checks if 
                #any of the RSS feeds are out of date, and updates them.
                #And also update the HTML template.
                #That version isn't much faster in practice considering that 
                #everything here is cached. However, it would help
                #for cases where the web server is temporarily down or slow, so 
                #just continuing to serve stale data until something new is found.

                #There needs to be logic to not start serving pages until all caches
                #are warm.

                #It takes just a few seconds to fetch all the feeds to my server
                #I could make them each fetch be in a threadpool to go faster also. 
                #Given the levels of caching, this app is usually very fast.

                print ("Warning: parsing from remote site %s" %(url))
                res = feedparser.parse(url)
                feedinfo = list(itertools.islice(res['entries'], 8))
                g_c.Put(url, feedinfo, timeout = expire_time + jitter)

            #First try to grab image from cache
            # image_name = g_c.Get(rssurl + ":" + "IMAGE")
            # if image_name is None:
            #     image_name = GrabImage(feedinfo)
            #     if image_name is not None:
            #         g_c.Put(rssurl + ":" + "IMAGE", image_name, timeout = EXPIRE_DAYS)
            #         print (image_name)    

            template = render_template('sitebox.html', entries = feedinfo, logo = logo_url, link = site_url)
            g_c.Put(site_url, template, timeout = expire_time + jitter + 10)
    
        result[cur_col].append(template)

        cur_col += 1
        cur_col %= 3

    result[0] = Markup(''.join(result[0]))
    result[1] = Markup(''.join(result[1]))
    result[2] = Markup(''.join(result[2]))

    page = render_template('page.html', columns = result)

    if page_order_s == g_standard_order_s:
        g_c.Put(page_order_s + suffix, page, timeout = EXPIRE_MINUTES)
    return page      

class ROStringField(StringField):
    def __call__(self, *args, **kwargs):
        kwargs.setdefault('readonly', True)
        return super(ROStringField, self).__call__(*args, **kwargs)

class UrlForm(Form):
    pri = IntegerField('Priority')
    url = ROStringField('RSS URL')

class CustomRSSForm(Form):
    pri = IntegerField('Priority')
    url = StringField('RSS URL', [validators.Length(min=10, max=120)])


class ConfigForm(Form):
    delete_cookie = BooleanField(label = "Delete Cookie")
    urls = FieldList(FormField(UrlForm))
    url_custom = FieldList(FormField(CustomRSSForm))

#    color = BooleanField('White background')
#  {{ render_field(form.color) }}


@g_app.route('/config', methods=['GET', 'POST'])
def Config():
    if request.method == 'GET':
        form = ConfigForm()

        page_order = request.cookies.get('RssUrls')
        if page_order is not None:
            page_order = json.loads(page_order)
        else:
            page_order = list(site_urls.keys())

        custom_count = 0
        for i, p_url in enumerate(page_order):
            site_info = site_urls.get(p_url, None)
            if site_info is not None and site_info[0] != "http://keithcu.com/images/Custom.png":
                urlf = UrlForm()
                urlf.pri = (i + 1) * 10
                urlf.url = p_url
                form.urls.append_entry(urlf)
            else:
                custom_count += 1
                rssf =  CustomRSSForm()
                rssf.url = p_url
                rssf.pri = (i + 1) * 10
                form.url_custom.append_entry(rssf)

        for i in range (custom_count, 5):
            rssf =  CustomRSSForm()
            rssf.url = "http://"
            rssf.pri = (i + 10) * 10
            form.url_custom.append_entry(rssf)

        page = render_template('config.html', form = form)
        return page
    else: #request == 'POST':
        form = ConfigForm(request.form)
        if form.delete_cookie.data:
            resp = g_app.make_response("<HTML><BODY>Deleted cookie.</BODY></HTML>")        
            resp.set_cookie('RssUrls', '', max_age = 0)
            return resp

        page_order = []

        urls = list(form.urls)

        url_custom = list(form.url_custom)
        for site in url_custom:
            if site.url.data != "http://":
                urls.append(site)

        urls.sort(key = lambda x: x.pri.data)

        for urlf in urls:
            if isinstance(urlf.form, UrlForm):
                page_order.append(urlf.url.data)
            elif isinstance(urlf.form, CustomRSSForm):
                page_order.append(urlf.url.data)
        
        #Pickle this stuff to a string to send as a cookie
        cookie_str = json.dumps(page_order)
        resp = g_app.make_response("<HTML><BODY>Saved cookie for later.</BODY></HTML>")        
        resp.set_cookie('RssUrls', cookie_str, max_age = EXPIRE_YEARS)
        return resp

