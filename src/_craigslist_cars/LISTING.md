# RapidAPI Listing Info — Craigslist Cars

## API Name (short title)
```
Craigslist Cars
```

## Short Description (one-liner shown in search results)
```
Live car listings scraped from Craigslist — price, mileage, year, city, state, and image URL.
```

## Long Description (shown on the API page)
```
Real-time access to used car listings crawled directly from Craigslist.

Each record includes:
- title       – listing title as posted
- year        – model year of the vehicle
- price       – asking price (integer, USD)
- mileage     – odometer reading (integer, miles)
- city        – city where the listing was posted
- state       – US state abbreviation
- country     – country code
- image_url   – direct URL to the listing's primary photo
- url         – original Craigslist listing URL
- posted_at   – timestamp the listing was posted
- crawled_at  – timestamp the record was collected

Great for price tracking, market research, dealership tools, or building car-search apps.
```

## Category (RapidAPI)
```
Data
```

---

## RapidAPI Body Schema (paste into Schema tab)
```json
{
  "type": "object",
  "properties": {
    "select": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Fields to return. Use [\"*\"] for all fields."
    },
    "filter": {
      "type": "object",
      "description": "Field filters. Supported operators: $gte, $lte, $gt, $lt, $eq, $ne, $like, $in.",
      "properties": {
        "title":      { "type": "string",  "description": "Listing headline" },
        "price":      { "type": "integer", "description": "Asking price in USD" },
        "mileage":    { "type": "integer", "description": "Odometer reading in miles" },
        "year":       { "type": "integer", "description": "Model year" },
        "url":        { "type": "string",  "description": "Direct link to listing" },
        "image_url":  { "type": "string",  "description": "Primary listing image" },
        "city":       { "type": "string",  "description": "City where listing was crawled" },
        "state":      { "type": "string",  "description": "State or province" },
        "country":    { "type": "string",  "description": "Country of origin" },
        "crawled_at": { "type": "string",  "description": "Timestamp when row was ingested" }
      }
    },
    "order_by": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field":     { "type": "string" },
          "direction": { "type": "string", "enum": ["asc", "desc"] }
        }
      }
    },
    "page_number": { "type": "integer", "description": "1-based page number." },
    "offset":      { "type": "integer", "description": "Row offset, alternative to page_number." }
  }
}
```

## RapidAPI Example Body (paste into Body tab)
```json
{
  "select": ["*"],
  "filter": {
    "price":   { "$gte": 1000, "$lte": 15000 },
    "mileage": { "$lt": 150000 },
    "year":    { "$gte": 2010 },
    "state":   { "$in": ["TX", "CA"] }
  },
  "order_by": [{ "field": "price", "direction": "asc" }],
  "page_number": 1
}
```
