DataMarketplace — Crawler Roadmap
===================================
Legend: [ ] not started  [~] in progress  [x] done  [!] cant be crawled

===========================================================================
INFRASTRUCTURE
===========================================================================

[ ] Git LFS — automated install & usage tooling
[ ] Housing type keyword detection on existing real estate crawlers
    keywords: apt, apartment, condo, townhouse, studio, bachelor,
              loft, duplex, triplex, basement, semi-detached
    action:   tag a housing_type field on every listing row

===========================================================================
REAL ESTATE & RENTALS
===========================================================================

[~] _craigslist_realestate     running
[ ] _redfin                    US listings, prices, estimates
[ ] _realtor_ca                Canadian MLS listings
[ ] _rentals_ca                Canadian rentals
[ ] _zumper                    US + CA rent
[ ] _padmapper                 aggregator, pulls from many sources
[ ] _kijiji_realestate         CA classifieds — real estate section
[ ] _loopnet                   commercial real estate

[!] Zillow                     blocked, dont bother
[!] Facebook Marketplace       login required, blocked

===========================================================================
AUTOMOTIVE
===========================================================================

[~] _craigslist_cars           running
[ ] _bringatrailer             auction results + active listings
[ ] _edmunds                   pricing, reviews, specs
[ ] _cargurus                  US listings + price history
[ ] _autotrader_us             US listings
[ ] _autotrader_ca             CA listings (different site)
[ ] _cars_com                  US listings
[ ] _carfax_listings           used car listings
[ ] _kijiji_autos              CA classifieds — autos section
[ ] _caranddriver              reviews + specs
[ ] _motortrend                reviews

===========================================================================
EBAY  (one crawler per category)
===========================================================================

[ ] _ebay_electronics          phones, laptops, tablets, audio
[ ] _ebay_motors               cars, trucks, parts & accessories
[ ] _ebay_fashion              clothing, shoes, accessories
[ ] _ebay_home_garden          furniture, tools, appliances
[ ] _ebay_sporting_goods       fitness, outdoor, bikes
[ ] _ebay_collectibles         coins, trading cards, antiques
[ ] _ebay_toys_hobbies         lego, diecast, games
[ ] _ebay_musical_instruments  guitars, synths, studio gear
[ ] _ebay_industrial           business equipment, parts

===========================================================================
KIJIJI  (one crawler per category)
===========================================================================

[ ] _kijiji_electronics        phones, laptops, etc.
[ ] _kijiji_furniture          sofas, beds, desks
[ ] _kijiji_appliances         washers, fridges, etc.
[ ] _kijiji_tools              power tools, hand tools
[ ] _kijiji_sporting_goods     bikes, skis, weights
[ ] _kijiji_toys_games         kids stuff, board games
[ ] _kijiji_clothing           apparel, shoes
[ ] _kijiji_pets               animals, supplies
[ ] _kijiji_services           local services
[ ] _kijiji_free               free stuff section
    note: kijiji_realestate and kijiji_autos listed in their own sections above

===========================================================================
AMAZON  (one crawler per category — check for CF first)
===========================================================================

[ ] _amazon_electronics        phones, laptops, audio
[ ] _amazon_home_kitchen       appliances, cookware, decor
[ ] _amazon_books              bestsellers, new releases
[ ] _amazon_clothing           apparel, shoes
[ ] _amazon_sports_outdoors    fitness, camping, bikes
[ ] _amazon_toys_games         kids, board games, puzzles
    warning: heavy bot protection — may need alt approach

===========================================================================
OTHER E-COMMERCE
===========================================================================

[ ] _canada_computers          PC parts, peripherals, laptops
[ ] _newegg                    PC parts — no CF
[ ] _bestbuy_ca                electronics — check CF
[ ] _bestbuy_us                electronics — check CF
[ ] _walmart_ca                general — check CF
[ ] _walmart_us                general — check CF
[ ] _target                    general — check CF
[ ] _costco                    bulk / warehouse deals
[ ] _aliexpress                global marketplace

[!] Amazon main search         CF / bot detection heavy

===========================================================================
JOBS & CAREER
===========================================================================

[~] _craigslist_jobs           running
[~] _canadian_jobbank          running
[ ] _indeed                    large job board
[ ] _glassdoor                 reviews + salary benchmarks
[ ] _simplyhired               job aggregator
[ ] _workopolis                CA job board
[ ] _monster                   job board
[ ] _weworkremotely            remote jobs
[ ] _remoteok                  remote jobs

[!] LinkedIn                   impossible — bot detection + legal risk

===========================================================================
FINANCE, CRYPTO & MARKETS
===========================================================================

[ ] _forex_rates               live + historical exchange rates
[ ] _stock_tickers             equities, ETFs — Yahoo Finance / others
[ ] _sec_edgar                 SEC filings, 10-K, 8-K, etc.
[ ] _crypto_historical         tick-level OHLCV data for backtesting
[ ] _binance                   spot prices, order book snapshots
[ ] _coinbase                  prices, trading pairs
[ ] _crunchbase                funding rounds, exec info, valuation
[ ] _llm_cost_tracker          token pricing across OpenAI, Anthropic, etc.
[ ] _sports_betting            odds from DraftKings, Covers, etc.
[ ] _alcohol_arb               price spread across LCBO, SAQ, BC Liquor, etc.
[ ] _cannabis_prices           legal dispensary pricing by province/state

===========================================================================
GAMING & ENTERTAINMENT
===========================================================================

[ ] _steam                     game prices, reviews, tags, player counts
[ ] _imdb                      movies, shows, ratings, cast
[ ] _igdb                      game metadata — has a free API
[ ] _newgrounds                games, art, scores
[ ] _leaderboard_fortnite      competitive rankings
[ ] _leaderboard_lol           League of Legends ranked ladder
[ ] _leaderboard_runescape     Hiscores — has a public API
[ ] _leaderboard_apex          Apex Legends ranked
[ ] _discogs                   music releases, vinyl market prices
[ ] _musicbrainz               open music metadata DB — has API

===========================================================================
ADULT CONTENT
===========================================================================

[ ] _xvideos
[ ] _pornhub
[ ] _xhamster
[ ] _xnxx
[ ] _redtube
[ ] _youporn
[ ] _spankbang
[ ] _eporner
[ ] _hqporner
[ ] _tnaflix
[ ] _motherless
    note: all generally scrapeable — metadata only (title, tags, views, duration)
    skip: daftsex, pornflip, pornzog, veporn — low quality / low traffic

===========================================================================
MEDIA & CONTENT
===========================================================================

[ ] _youtube_data              channel stats, video metadata, view counts
[ ] _youtube_transcripts       transcript extraction via youtube-transcript-api
[ ] _news_aggregator           RSS feeds — BBC, Reuters, AP, CBC, Globe, etc.
[ ] _reddit                    subreddit posts + comments (public JSON API)
[ ] _wine_data                 Vivino ratings, LCBO wine listings
[ ] _spirits_data              whisky/rum/gin databases

===========================================================================
TRAVEL & LOGISTICS
===========================================================================

[ ] _flight_data               fares + schedules — Google Flights / others
[ ] _shipping_rates            UPS, FedEx, Canada Post rate calculators
[ ] _weather                   OpenMeteo — free, no CF, excellent API
[ ] _holidays_db               public holidays by country/province

===========================================================================
B2B & INTELLIGENCE
===========================================================================

[ ] _b2b_lead_enrichment       email → company size, revenue, tech stack
[ ] _global_sanctions          OFAC, UN, EU consolidated lists
[ ] _dns_lookup                domain → registrar, A/MX/NS records, WHOIS

===========================================================================
UTILITIES / TOOL APIs  (not crawls — compute endpoints)
===========================================================================

[ ] _ocr                       image → text
[ ] _qr_code_gen               text/URL → QR PNG
[ ] _doc_converter             HTML→MD, PDF→text, DOCX→MD, etc.
[ ] _duckduckgo_search         SERP scrape — no API key needed

===========================================================================
LIFESTYLE & MISC
===========================================================================

[ ] _recipes                   AllRecipes, Food Network, etc.
[ ] _weed_sites                dispensary menus — Leafly, Weedmaps
[ ] _wine_spirits              (see Media section above — merge TBD)

===========================================================================
BLOCKED / IMPOSSIBLE — DO NOT ATTEMPT
===========================================================================

[!] LinkedIn                   ceases & desist territory, heavy bot detection
[!] Zillow                     fully blocked
[!] Facebook / Marketplace     login wall + CF
[!] Instagram                  login wall
[!] Twitter / X                API paywalled, scraping blocked
[!] Google Maps / Places       ToS, bot detection
