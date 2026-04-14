import feedparser

URL = "https://ria.ru/export/rss2/index.xml"

feed = feedparser.parse(URL)
print("bozo:", feed.bozo, "entries:", len(feed.entries))
if feed.entries:
    e = feed.entries[0]
    print("keys:", list(e.keys()))
    for k in ["title", "summary", "description", "content", "content:encoded", "summary_detail", "yandex_fulltext"]:
        if k in e:
            print(k, "->", str(e[k])[:200])
