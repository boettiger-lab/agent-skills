"""Render HTML figure sources to PNG + vector PDF with headless Chromium.

Usage: python3 build.py [name ...]   (default: every *.html here)
Templates may use {{icon:NAME}} for an inline Lucide icon (fetched once from
unpkg into icons/, ISC license) and {{json:relative/path.json}} to inline data. Each page must wrap the figure in #fig.
"""
import os, re, sys, glob, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")
CHROME = (sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome")))
          or [None])[-1]  # None -> Playwright's bundled browser
LUCIDE = "https://unpkg.com/lucide-static@0.469.0/icons/{}.svg"


def icon(name):
    path = os.path.join(HERE, "icons", f"{name}.svg")
    if not os.path.exists(path):
        svg = urllib.request.urlopen(LUCIDE.format(name)).read().decode()
        open(path, "w").write(svg)
    svg = open(path).read()
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S).strip()
    return svg.replace('class="lucide', f'class="ic lucide')


def build(src, browser):
    name = os.path.splitext(os.path.basename(src))[0]
    html = open(src).read()
    html = re.sub(r"\{\{icon:([a-z0-9-]+)\}\}", lambda m: icon(m.group(1)), html)
    html = re.sub(r"\{\{json:([^}]+)\}\}", lambda m: open(os.path.join(HERE, m.group(1))).read(), html)
    tmp = os.path.join(HERE, "_build", f"{name}.html")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, "w").write(html)
    page = browser.new_page(device_scale_factor=3, viewport={"width": 1400, "height": 1200})
    page.goto("file://" + tmp)
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    fig = page.locator("#fig")
    fig.screenshot(path=os.path.join(OUT, f"{name}.png"), omit_background=False)
    box = fig.bounding_box()
    page.emulate_media(media="screen")
    page.add_style_tag(content="@page{margin:0} html,body{margin:0;padding:0}")
    page.pdf(path=os.path.join(OUT, f"{name}.pdf"), width=f"{box['width']}px",
             height=f"{box['height'] + 1}px", print_background=True, page_ranges="1")
    page.close()
    print("built", name, int(box["width"]), "x", int(box["height"]))


if __name__ == "__main__":
    names = sys.argv[1:] or [os.path.splitext(os.path.basename(f))[0]
                             for f in glob.glob(os.path.join(HERE, "*.html"))]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME)
        for n in names:
            build(os.path.join(HERE, f"{n}.html"), b)
        b.close()
