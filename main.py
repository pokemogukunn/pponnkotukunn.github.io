import json
import requests
import urllib.parse
import time
import datetime
import random
import os
from cache import cache
from fastapi import FastAPI, Depends, Response, Cookie, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.responses import RedirectResponse as redirect
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Union, Optional

max_api_wait_time = 3
max_time = 10
apis = [r"https://youtube.076.ne.jp/", r"https://vid.puffyan.us/", r"https://inv.riverside.rocks/", r"https://invidio.xamh.de/", r"https://y.com.sb/", r"https://invidious.sethforprivacy.com/", r"https://invidious.tiekoetter.com/", r"https://inv.bp.projectsegfau.lt/", r"https://inv.vern.cc/", r"https://invidious.nerdvpn.de/", r"https://inv.privacy.com.de/", r"https://invidious.rhyshl.live/", r"https://invidious.slipfox.xyz/", r"https://invidious.weblibre.org/", r"https://invidious.namazso.eu/"]
url = requests.get(r'https://raw.githubusercontent.com/mochidukiyukimi/yuki-youtube-instance/main/instance.txt').text.rstrip()
version = "1.0"

apichannels = []
apicomments = []
[[apichannels.append(i), apicomments.append(i)] for i in apis]

class APItimeoutError(Exception):
    pass

def is_json(json_str):
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False

def apirequest(url):
    global apis
    global max_time
    starttime = time.time()
    for api in apis:
        if time.time() - starttime >= max_time - 1:
            break
        try:
            res = requests.get(api + url, timeout=max_api_wait_time)
            if res.status_code == 200 and is_json(res.text):
                return res.text
            else:
                print(f"エラー: {api}")
                apis.append(api)
                apis.remove(api)
        except:
            print(f"タイムアウト: {api}")
            apis.append(api)
            apis.remove(api)
    raise APItimeoutError("APIがタイムアウトしました")

def apichannelrequest(url):
    global apichannels
    global max_time
    starttime = time.time()
    for api in apichannels:
        if time.time() - starttime >= max_time - 1:
            break
        try:
            res = requests.get(api + url, timeout=max_api_wait_time)
            if res.status_code == 200 and is_json(res.text):
                return res.text
            else:
                print(f"エラー: {api}")
                apichannels.append(api)
                apichannels.remove(api)
        except:
            print(f"タイムアウト: {api}")
            apichannels.append(api)
            apichannels.remove(api)
    raise APItimeoutError("APIがタイムアウトしました")

def apicommentsrequest(url):
    global apicomments
    global max_time
    starttime = time.time()
    for api in apicomments:
        if time.time() - starttime >= max_time - 1:
            break
        try:
            res = requests.get(api + url, timeout=max_api_wait_time)
            if res.status_code == 200 and is_json(res.text):
                return res.text
            else:
                print(f"エラー: {api}")
                apicomments.append(api)
                apicomments.remove(api)
        except:
            print(f"タイムアウト: {api}")
            apicomments.append(api)
            apicomments.remove(api)
    raise APItimeoutError("APIがタイムアウトしました")

def get_info(request):
    global version
    return json.dumps([version, os.environ.get('RENDER_EXTERNAL_URL'), str(request.scope["headers"]), str(request.scope['router'])[39:-2]])

def get_data(videoid):
    t = json.loads(apirequest(r"api/v1/videos/" + urllib.parse.quote(videoid)))
    return [{"id": i["videoId"], "title": i["title"], "authorId": i["authorId"], "author": i["author"]} for i in t["recommendedVideos"]], list(reversed([i["url"] for i in t["formatStreams"]]))[:2], t["descriptionHtml"].replace("\n", "<br>"), t["title"], t["authorId"], t["author"], t["authorThumbnails"][-1]["url"]

def get_search(q, page):
    t = json.loads(apirequest(fr"api/v1/search?q={urllib.parse.quote(q)}&page={page}&hl=jp"))
    def load_search(i):
        if i["type"] == "video":
            return {"title": i["title"], "id": i["videoId"], "authorId": i["authorId"], "author": i["author"], "length": str(datetime.timedelta(seconds=i["lengthSeconds"])), "published": i["publishedText"], "type": "video"}
        elif i["type"] == "playlist":
            return {"title": i["title"], "id": i["playlistId"], "thumbnail": i["videos"][0]["videoId"], "count": i["videoCount"], "type": "playlist"}
        else:
            if i["authorThumbnails"][-1]["url"].startswith("https"):
                return {"author": i["author"], "id": i["authorId"], "thumbnail": i["authorThumbnails"][-1]["url"], "type": "channel"}
            else:
                return {"author": i["author"], "id": i["authorId"], "thumbnail": r"https://" + i["authorThumbnails"][-1]["url"], "type": "channel"}
    return [load_search(i) for i in t]

def get_channel(channelid):
    global apichannels
    t = json.loads(apichannelrequest(r"api/v1/channels/" + urllib.parse.quote(channelid)))
    if t["latestVideos"] == []:
        print("APIがチャンネルを返しませんでした")
        apichannels.append(apichannels[0])
        apichannels.remove(apichannels[0])
        raise APItimeoutError("APIがチャンネルを返しませんでした")
    return [[{"title": i["title"], "id": i["videoId"], "authorId": t["authorId"], "author": t["author"], "published": i["publishedText"], "type": "video"} for i in t["latestVideos"]], {"channelname": t["author"], "channelicon": t["authorThumbnails"][-1]["url"], "channelprofile": t["descriptionHtml"]}]

def get_playlist(listid, page):
    t = json.loads(apirequest(r"/api/v1/playlists/" + urllib.parse.quote(listid) + "?page=" + urllib.parse.quote(page)))["videos"]
    return [{"title": i["title"], "id": i["videoId"], "authorId": i["authorId"], "author": i["author"], "type": "video"} for i in t]

def get_comments(videoid):
    t = json.loads(apicommentsrequest(r"api/v1/comments/" + urllib.parse.quote(videoid)))
    return [{"author": i["author"], "comment": i["contentHtml"], "authorThumbnails": i["authorThumbnails"][-1]["url"], "published": i["published"]} for i in t]

def check_cookie(cookie):
    return cookie is not None

app = FastAPI()
app.add_middleware(GZipMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get('/', response_class=HTMLResponse)
def index(response: Response, request: Request):
    return template('index.html', {"request": request, "videos": cache})

@app.get('/health', response_class=PlainTextResponse)
def health_check():
    return "OK"

@app.get('/video', response_class=HTMLResponse)
def video(videoid: str, response: Response, request: Request, yuki: Union[str] = Cookie(None)):
    if not check_cookie(yuki):
        return redirect("/")
    response.set_cookie(key="yuki", value="True", max_age=7*24*60*60)
    t = get_data(videoid)
    return template('video.html', {"request": request, "videos": t[0], "videofiles": t[1], "description": t[2], "title": t[3], "channelid": t[4], "author": t[5], "authoricon": t[6], "proxy": proxy})

@app.get('/search', response_class=HTMLResponse)
def search(q: str, page: Optional[int] = 1, response: Response, request: Request, yuki: Union[str] = Cookie(None)):
    if not check_cookie(yuki):
        return redirect("/")
    response.set_cookie(key="yuki", value="True", max_age=7*24*60*60)
    return template('search.html', {"request": request, "search": get_search(q, page), "q": q})

@app.get('/playlist', response_class=HTMLResponse)
def playlist(listid: str, page: Optional[int] = 1, response: Response, request: Request, yuki: Union[str] = Cookie(None)):
    if not check_cookie(yuki):
        return redirect("/")
    response.set_cookie(key="yuki", value="True", max_age=7*24*60*60)
    return template('playlist.html', {"request": request, "videos": get_playlist(listid, page)})

@app.get('/comments', response_class=HTMLResponse)
def comments(videoid: str, response: Response, request: Request, yuki: Union[str] = Cookie(None)):
    if not check_cookie(yuki):
        return redirect("/")
    response.set_cookie(key="yuki", value="True", max_age=7*24*60*60)
    return template('comments.html', {"request": request, "comments": get_comments(videoid)})

@app.get('/channel', response_class=HTMLResponse)
def channel(channelid: str, response: Response, request: Request, yuki: Union[str] = Cookie(None)):
    if not check_cookie(yuki):
        return redirect("/")
    response.set_cookie(key="yuki", value="True", max_age=7*24*60*60)
    t = get_channel(channelid)
    return template('channel.html', {"request": request, "videos": t[0], "channeldata": t[1]})

@app.get("/calculator", response_class=HTMLResponse)
def calc(response: Response, request: Request, yuki: Union[str] = Cookie(None)):
    response.set_cookie("yuki", "True", max_age=60 * 60 * 24 * 7)
    return template("calculator.html", {"request": request})
