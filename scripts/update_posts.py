"""블로그 RSS(jekyll-feed)에서 최근 글 5개를 README의 POSTS 마커 사이에 채운다."""
import re, sys, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path

FEED = "https://cjsan30.github.io/feed.xml"
README = Path("README.md")
LIMIT = 5

raw = urllib.request.urlopen(FEED, timeout=20).read()
root = ET.fromstring(raw)
ns = {"a": "http://www.w3.org/2005/Atom"}
posts = []
for e in root.findall("a:entry", ns)[:LIMIT]:
    title = (e.findtext("a:title", "", ns) or "").strip()
    link = e.find("a:link", ns).get("href")
    date = (e.findtext("a:published", "", ns) or e.findtext("a:updated", "", ns))[:10]
    posts.append(f"- [{title}]({link}) <sub>{date}</sub>")

if not posts:
    sys.exit("글이 없어 README를 건드리지 않음")

block = "<!-- POSTS:START -->\n### 최근 글\n\n" + "\n".join(posts) + "\n<!-- POSTS:END -->"
text = README.read_text(encoding="utf-8")
new = re.sub(r"<!-- POSTS:START -->.*?<!-- POSTS:END -->", lambda _: block, text, flags=re.S)
if new != text:
    README.write_text(new, encoding="utf-8")
