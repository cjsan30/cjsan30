#!/usr/bin/env python3
"""GitHub 잔디(공개 기여 달력) 데이터로 '1년간의 커밋' 애니메이션 SVG를 만듭니다.

- 표준 라이브러리만 사용합니다(pip 설치 불필요).
- 데이터: https://github.com/users/<아이디>/contributions (공식 잔디와 같은 데이터)
- 출력: assets/commit-year.svg(애니메이션), assets/commit-year-static.svg(움직임 없는 완성본)
- 데이터를 못 가져오거나 형식이 달라졌으면 기존 파일을 건드리지 않고 오류로 종료합니다.
"""
import calendar, os, random, re, sys, time, urllib.request
from datetime import date

USER = os.environ.get("GITHUB_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "cjsan30"
OUT_DIR = os.environ.get("OUT_DIR", "assets")
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'D2Coding', monospace"
SANS = "-apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif"
BG = "#12163a"

# ---------------------------------------------------------------- 데이터
def fetch_counts(user, tries=3):
    url = f"https://github.com/users/{user}/contributions"
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (commit-year-graphic)", "Accept-Language": "en-US,en;q=0.9"})
            html_ = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            cells = {}
            for tag in re.findall(r"<td\b[^>]*>", html_):
                d = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', tag); i_ = re.search(r'\bid="([^"]+)"', tag)
                if d and i_: cells[i_.group(1)] = d.group(1)
            counts = {}
            for cid, text in re.findall(r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', html_):
                if cid not in cells: continue
                m = re.search(r"(\d[\d,]*)\s+contribution", text)
                counts[cells[cid]] = int(m.group(1).replace(",", "")) if m else 0
            if len(counts) < 300:
                raise RuntimeError(f"잔디 데이터를 충분히 읽지 못했습니다({len(counts)}일). GitHub 페이지 형식이 바뀌었을 수 있어요.")
            return counts
        except Exception as e:                      # 네트워크/형식 오류 → 재시도
            last = e; time.sleep(3*(i+1))
    raise SystemExit(f"데이터 가져오기 실패: {last}")

def build_months(counts):
    today = date.fromisoformat(max(counts))         # 페이지의 마지막 날짜 = 오늘
    y, m = today.year, today.month - 11
    while m <= 0: m += 12; y -= 1
    months = []
    for _ in range(12):
        nd = calendar.monthrange(y, m)[1]
        days = [None if date(y, m, d) > today else counts.get(date(y, m, d).isoformat(), 0) for d in range(1, nd+1)]
        months.append(dict(label=f"{m}월", y=y, m=m, nd=nd, days=days))
        m += 1
        if m > 12: m, y = 1, y+1
    allc = sorted(c for mo in months for c in mo["days"] if c)
    if allc:
        q = lambda p: allc[min(len(allc)-1, int(len(allc)*p))]
        t = [q(.25), q(.5), q(.75)]
        lv = lambda c: 0 if not c else 1 if c <= t[0] else 2 if c <= t[1] else 3 if c <= t[2] else 4
    else:
        lv = lambda c: 0
    return dict(months=months, lv=lv)

# ---------------------------------------------------------------- 그리기
def build(D):
    W, H, x0, x1, gap, CY = 800, 262, 40, 760, 5, 234
    DUR, SWEEP, FADE_S = 14, 8, 1; SW = SWEEP/DUR      # 14초 주기: 8초 훑기 → 5초 유지 → 1초 페이드아웃 후 반복
    lv = D["lv"]; r = random.Random(4); hb = [2, 8, 17, 28, 40]
    items = [(mi, d, lv(c)) for mi, mo in enumerate(D["months"]) for d, c in enumerate(mo["days"]) if c is not None]
    pitch = (x1-x0-11*gap)/len(items)
    x = x0; last = -1; pos = {}; bars = []
    for mi, d, L in items:
        if mi != last and last != -1: x += gap
        last = mi; pos[(mi, d)] = x
        h = hb[L]*(r.uniform(.82, 1.08) if L else 1)
        bars.append(f'<rect x="{x:.2f}" y="{128-h:.1f}" width="{pitch*.66:.2f}" height="{h*2:.1f}" rx=".6"/>')
        x += pitch
    end = x
    tf = lambda xp: max(0, (xp-x0)/(end-x0)*SW)
    A = f'dur="{DUR}s" repeatCount="indefinite"'
    FADE = f'<animate attributeName="opacity" dur="{DUR}s" repeatCount="indefinite" keyTimes="0;{(DUR-FADE_S)/DUR:.4f};1" values="1;1;0"/>'

    weeks = []
    for mi, mo in enumerate(D["months"]):
        b = [0, 7, 14, 21, mo["nd"]]
        for wk in range(4):
            ds = [d for d in range(b[wk], b[wk+1]) if mo["days"][d] is not None]
            if not ds: continue
            weeks.append((mi, wk, pos[(mi, ds[0])], pos[(mi, ds[-1])]+pitch, sum(lv(mo["days"][d]) for d in ds)/len(ds)))
    mxm = max(w[4] for w in weeks) or 1; q = lambda m: round(m/mxm*4)
    lit = ["#8a6a45", "#c08a4a", "#e8a94e", "#ffc857", "#fff1c0"]; unlit = ["#262b5c", "#2f3672", "#3a4590", "#4a56ad", "#5b6bd0"]
    seg_h = [6, 10, 14, 18, 22]; dim, bright, ruler = [], [], []
    for mi, wk, xs, xe, m in weeks:
        k = q(m); hgt = seg_h[k]
        rect = lambda fill: f'<rect x="{xs+.8:.1f}" y="{CY-hgt/2:.1f}" width="{xe-xs-1.6:.1f}" height="{hgt}" rx="3" fill="{fill}"/>'
        dim.append(rect(unlit[k])); bright.append(rect(lit[k]))
        ms_ = wk == 0
        ruler.append(f'<line x1="{xs:.1f}" y1="176" x2="{xs:.1f}" y2="{189 if ms_ else 183}" stroke="{"#8e9bff" if ms_ else "#4a5199"}" stroke-width="{1.5 if ms_ else 1}"/>')
    ruler.append(f'<line x1="{end:.1f}" y1="176" x2="{end:.1f}" y2="189" stroke="#8e9bff" stroke-width="1.5"/><line x1="{x0}" y1="176" x2="{end:.1f}" y2="176" stroke="#3a4080"/>')
    spans = {}
    for mi, wk, xs, xe, m in weeks:
        a, b = spans.get(mi, (xs, xe)); spans[mi] = (min(a, xs), max(b, xe))
    lab = "".join(f'<text x="{(a+b)/2:.0f}" y="207" text-anchor="middle" font-family="{SANS}" font-size="12.5" fill="#aab2e0">{D["months"][mi]["label"]}</text>' for mi, (a, b) in spans.items())

    P = 5
    kt = "0;" + ";".join(f"{tf((w[2]+w[3])/2):.4f}" for w in weeks) + ";1"
    xs_ = [w[2]-P for w in weeks]; ws_ = [w[3]-w[2]+2*P for w in weeks]
    hx = ";".join(f"{v:.1f}" for v in [xs_[0]] + xs_ + [xs_[-1]]); hw = ";".join(f"{v:.1f}" for v in [ws_[0]] + ws_ + [ws_[-1]])
    hl = (f'<rect x="{xs_[-1]:.1f}" y="75" width="{ws_[-1]:.1f}" height="171" rx="6" fill="url(#bandg)">'
          f'<animate attributeName="x" {A} keyTimes="{kt}" values="{hx}"/>'
          f'<animate attributeName="width" {A} keyTimes="{kt}" values="{hw}"/></rect>')

    seq = [(tf(pos[(mi, d)]), mi, d+1) for mi, d, _ in items]
    def strip(idx_fn, rows_svg, row_h=16):
        pts = []; prev = None
        for t, mi, day in seq:
            v = idx_fn(mi, day)
            if v != prev: pts.append((t, v)); prev = v
        kt_ = ";".join(f"{t:.4f}" for t, _ in pts); vs = ";".join(f"0 {-row_h*v}" for _, v in pts)
        fin = -row_h*pts[-1][1]
        return (f'<g transform="translate(0,{fin})"><animateTransform attributeName="transform" type="translate" {A} calcMode="discrete" keyTimes="{kt_}" values="{vs}"/>{rows_svg}</g>')
    mon_rows = "".join(f'<text x="-6" y="{4+16*k}" text-anchor="end" font-family="{SANS}" font-size="11.5" font-weight="700" fill="#fff1c0">{mo["label"]}</text>' for k, mo in enumerate(D["months"]))
    tens_rows = "".join(f'<text x="7" y="{4+16*k}" text-anchor="middle" font-family="{MONO}" font-size="12" font-weight="700" fill="#fff1c0">{t}</text>' for k, t in enumerate(["", "1", "2", "3"]) if t)
    ones_rows = "".join(f'<text x="14.5" y="{4+16*k}" text-anchor="middle" font-family="{MONO}" font-size="12" font-weight="700" fill="#fff1c0">{k}</text>' for k in range(10))
    px_end = end-20
    counter = (f'<g transform="translate({px_end:.1f} 61)"><animateTransform attributeName="transform" type="translate" {A} keyTimes="0;{SW};1" values="{x0} 61;{px_end:.1f} 61;{px_end:.1f} 61"/>'
               '<rect x="-38" y="-10" width="72" height="20" rx="10" fill="#0b0e24" fill-opacity=".92" stroke="#3a4080"/>'
               f'<g clip-path="url(#cm)">{strip(lambda mi, day: mi, mon_rows)}</g>'
               f'<g clip-path="url(#ct)">{strip(lambda mi, day: 0 if day < 10 else day//10, tens_rows)}</g>'
               f'<g clip-path="url(#co)">{strip(lambda mi, day: day % 10, ones_rows)}</g>'
               f'<text x="20" y="4" font-family="{SANS}" font-size="11" fill="#c8cdf0">일</text></g>')
    ph_anim = lambda attr: f'<animate attributeName="{attr}" {A} keyTimes="0;{SW};1" values="{x0};{end:.0f};{end:.0f}"/>'
    g = "".join(bars)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="최근 1년간의 일별 커밋 파형. 막대가 높을수록 많이 쓴 날이고, 아래 칸은 주 단위 활동량">'
            f'<defs><linearGradient id="bandg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff1c0" stop-opacity="0"/><stop offset=".28" stop-color="#fff1c0" stop-opacity=".22"/><stop offset=".72" stop-color="#fff1c0" stop-opacity=".22"/><stop offset="1" stop-color="#fff1c0" stop-opacity="0"/></linearGradient><clipPath id="pl"><rect x="0" y="0" width="{end:.0f}" height="{H}"><animate attributeName="width" {A} keyTimes="0;{SW};1" values="{x0};{end:.0f};{end:.0f}"/></rect></clipPath>'
            '<clipPath id="cm"><rect x="-33" y="-7" width="29" height="14"/></clipPath><clipPath id="ct"><rect x="2.5" y="-7" width="9" height="14"/></clipPath><clipPath id="co"><rect x="10" y="-7" width="9" height="14"/></clipPath></defs>'
            f'<rect width="{W}" height="{H}" rx="14" fill="{BG}"/>' + f'<g>{FADE}{hl}</g>'
            + f'<text x="28" y="38" font-family="{SANS}" font-size="20" font-weight="700" fill="#e8ebff">1년간의 커밋</text>'
            + f'<text x="772" y="37" text-anchor="end" font-family="{SANS}" font-size="13" fill="#aab2e0">막대가 높을수록 많이 쓴 날</text>'
            + f'<g fill="#6b75d6" opacity=".38">{g}</g><g clip-path="url(#pl)"><g fill="#ffc857">{FADE}{g}</g></g>'
            + f'<line x1="{x0}" y1="128" x2="{end:.0f}" y2="128" stroke="#e8ebff" stroke-width=".5" opacity=".25"/>'
            + "".join(ruler) + lab + "".join(dim) + f'<g clip-path="url(#pl)"><g>{FADE}{"".join(bright)}</g></g>'
            + f'<g>{FADE}<line x1="{end:.1f}" y1="73" x2="{end:.1f}" y2="192" stroke="#fff1c0" stroke-width="5" opacity=".14">{ph_anim("x1")}{ph_anim("x2")}</line>'
            + f'<line x1="{end:.1f}" y1="73" x2="{end:.1f}" y2="192" stroke="#fff1c0" stroke-width="1.2" opacity=".75">{ph_anim("x1")}{ph_anim("x2")}</line>'
            + f'<circle cx="{end:.1f}" cy="{CY}" r="6" fill="#fff1c0">{ph_anim("cx")}</circle>' + counter + '</g></svg>')

def main():
    counts = fetch_counts(USER)
    D = build_months(counts)
    svg = build(D)
    static = re.sub(r"<animate(?:Transform)?[^>]*/>", "", svg)
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, body in (("commit-year.svg", svg), ("commit-year-static.svg", static)):
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f: f.write(body)
    days = [c for mo in D["months"] for c in mo["days"] if c is not None]
    print(f"{USER}: {len(days)}일 중 커밋한 날 {sum(1 for c in days if c)}일, 총 {sum(days)}건, 하루 최대 {max(days)}건")

if __name__ == "__main__":
    main()
