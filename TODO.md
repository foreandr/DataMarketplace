# DataMarketplace — Crawler Roadmap

> Legend: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked/needs research

---

## ⚙️ Infrastructure

| # | Task | Notes |
|---|------|-------|
| 1 | `[ ]` **Git LFS** — automated install & usage tooling | Needed before large DB/binary assets |
| 2 | `[ ]` **Housing type keyword detection** | Scan listing text for: `apt`, `apartment`, `condo`, `townhouse`, `studio`, `bachelor`, `loft`, `duplex`, `triplex` → tag `housing_type` field |

---

## 🏠 Real Estate & Rentals

| # | Source | Notes |
|---|--------|-------|
| 1 | `[~]` Craigslist Real Estate | Running |
| 2 | `[ ]` **Redfin** | Zillow is blocked — prioritize this |
| 3 | `[ ]` Realtor.ca | Canadian listings |
| 4 | `[ ]` Rentals.ca | Canadian rentals |
| 5 | `[ ]` Zumper | US/CA rent |
| 6 | `[ ]` PadMapper | Aggregator |
| 7 | `[ ]` Kijiji Real Estate | CA classifieds |

---

## 🚗 Automotive

| # | Source | Notes |
|---|--------|-------|
| 1 | `[~]` Craigslist Cars | Running |
| 2 | `[ ]` **Bring a Trailer** | Auction data |
| 3 | `[ ]` **Edmunds** | Pricing & reviews |
| 4 | `[ ]` CarGurus | |
| 5 | `[ ]` AutoTrader | US & CA |
| 6 | `[ ]` Cars.com | |
| 7 | `[ ]` CarFax listings | |
| 8 | `[ ]` Kijiji Autos | CA |

---

## 🛒 E-Commerce & Price Comparison

| # | Source | Notes |
|---|--------|-------|
| 1 | `[ ]` **eBay** | By category |
| 2 | `[ ]` **Kijiji** | General categories |
| 3 | `[ ]` **Canada Computers** | Tech/PC parts |
| 4 | `[ ]` Best Buy | Check for CF |
| 5 | `[ ]` Walmart | Check for CF |
| 6 | `[ ]` Amazon | Check for CF |
| 7 | `[ ]` Target | Check for CF |
| 8 | `[ ]` Newegg | PC parts, no CF |

> ⚠️ Flag anything behind Cloudflare — skip or use alt method

---

## 💼 Jobs & Career

| # | Source | Notes |
|---|--------|-------|
| 1 | `[~]` Craigslist Jobs | Running |
| 2 | `[~]` Canadian Job Bank | Running |
| 3 | `[ ]` Indeed | |
| 4 | `[ ]` LinkedIn Jobs | |
| 5 | `[ ]` Glassdoor | Reviews + salary benchmarks |
| 6 | `[ ]` SimplyHired | |
| 7 | `[ ]` Workopolis | CA |

---

## 📈 Finance, Crypto & Markets

| # | Source | Notes |
|---|--------|-------|
| 1 | `[ ]` **Forex rates** | Live + historical |
| 2 | `[ ]` **Finance ticker data** | Stocks, ETFs |
| 3 | `[ ]` **SEC filings** | EDGAR |
| 4 | `[ ]` **Currency & Crypto** | Historical tick data (backtest-ready) |
| 5 | `[ ]` Binance | |
| 6 | `[ ]` Coinbase | |
| 7 | `[ ]` LLM Cost Tracker | Token pricing across providers |
| 8 | `[ ]` Crunchbase | Funding rounds, exec info |
| 9 | `[ ]` Sports betting odds | Covers, DraftKings, etc. |
| 10 | `[ ]` Alcohol arbitrage | Price spread across retailers |
| 11 | `[ ]` Cannabis price data | Dispensary/legal market |

---

## 🎮 Gaming & Entertainment

| # | Source | Notes |
|---|--------|-------|
| 1 | `[ ]` **Steam** | Prices, reviews, tags |
| 2 | `[ ]` **IMDB** | Movies, ratings, cast |
| 3 | `[ ]` **IGDB** (International Game DB) | Game metadata |
| 4 | `[ ]` Fortnite leaderboards | |
| 5 | `[ ]` League of Legends leaderboards | |
| 6 | `[ ]` RuneScape leaderboards | Hiscores API |
| 7 | `[ ]` Apex Legends leaderboards | |
| 8 | `[ ]` Music databases | Discogs, MusicBrainz, etc. |

---

## 📺 Media & Content

| # | Source | Notes |
|---|--------|-------|
| 1 | `[ ]` **YouTube data** | Channel stats, video metadata |
| 2 | `[ ]` **YouTube transcripts** | `youtube-transcript-api` |
| 3 | `[ ]` News aggregation | RSS feeds + scrapers |
| 4 | `[ ]` Social media | Reddit confirmed; others TBD |
| 5 | `[ ]` Wine & spirits data | Vivino, LCBO, etc. |

---

## 🧭 Travel & Logistics

| # | Source | Notes |
|---|--------|-------|
| 1 | `[ ]` **Flight data** | Fares, schedules |
| 2 | `[ ]` Shipping rates | UPS, FedEx, Canada Post |
| 3 | `[ ]` Weather | OpenMeteo (free, no CF) |
| 4 | `[ ]` Holidays DB | Public holidays by country |

---

## 🏢 B2B & Business Intelligence

| # | Source | Notes |
|---|--------|-------|
| 1 | `[ ]` **B2B Lead Enrichment** | `name@company.com` → size, revenue, tech stack |
| 2 | `[ ]` **Global Sanctions** | OFAC, UN, EU lists |
| 3 | `[ ]` DNS lookup | Domain → registrar, IP, MX, etc. |

---

## 🔧 Utilities & Tools (non-crawl APIs)

| # | Tool | Notes |
|---|------|-------|
| 1 | `[ ]` **OCR** | Image → text arbitrage |
| 2 | `[ ]` **QR code generator** | URL/text → QR PNG |
| 3 | `[ ]` **Document conversion** | HTML → MD, PDF → text, etc. |
| 4 | `[ ]` **DuckDuckGo search** | Scrape SERP results |

---

## 🍽️ Lifestyle & Misc

| # | Source | Notes |
|---|--------|-------|
| 1 | `[ ]` Recipes | AllRecipes, etc. |

xvideos.com
pornhub.com
xhamster.com
xnxx.com
redtube.com
youporn.com
tube8.com
eporner.com
spankbang.com
hqporner.com
daftsex.com
thumbzilla.com
porntrex.com
veporn.net
pornflip.com
pornzog.com
hclips.com
dinotube.com
youjizz.com
tnaflix.com
xfreehd.com
porn300.com
porn00.org
porn7.net
pornwhite.com
tubepornclassic.com
fuq.com
gotporn.com
analdin.com
pornhd.com
ixxx.com
sexu.com
motherless.com


    newgrounds

    alcohol arb
    weed sites