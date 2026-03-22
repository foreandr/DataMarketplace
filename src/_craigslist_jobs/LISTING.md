# RapidAPI Listing Info — Craigslist Jobs

## API Name (short title)
```
Craigslist Jobs
```

## Short Description (one-liner shown in search results)
```
Craigslist job postings with title, pay, posted date, and location.
```

## Long Description (shown on the API page)
```
Job listings scraped from Craigslist across US & Canadian cities. Records include title, hourly pay, posted date, full description text, listing URL, image when available, and geo-location tags captured at crawl time.
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
      "items": {
        "type": "string"
      },
      "description": "Fields to return. Use [\"*\"] for all fields."
    },
    "filter": {
      "type": "object",
      "description": "Field filters. Supported operators: $gte, $lte, $gt, $lt, $eq, $ne, $like, $in.",
      "properties": {
        "title": {
          "type": "string",
          "description": "Job title or listing headline"
        },
        "location": {
          "type": "string",
          "description": "Neighborhood or area label"
        },
        "posted_date": {
          "type": "string",
          "description": "Posting date as shown on Craigslist"
        },
        "pay": {
          "type": "number",
          "description": "Hourly pay rate (converted to hourly if provided as yearly/monthly)"
        },
        "employment_type": {
          "type": "string",
          "description": "Full-time, part-time, contract, temp, etc."
        },
        "description": {
          "type": "string",
          "description": "Full job description text"
        },
        "url": {
          "type": "string",
          "description": "Direct link to listing"
        },
        "image_url": {
          "type": "string",
          "description": "Primary listing image"
        },
        "city": {
          "type": "string",
          "description": "City where listing was crawled"
        },
        "state": {
          "type": "string",
          "description": "State or province"
        },
        "country": {
          "type": "string",
          "description": "Country of origin"
        },
        "crawled_at": {
          "type": "string",
          "description": "Timestamp when row was ingested"
        }
      }
    },
    "order_by": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": {
            "type": "string"
          },
          "direction": {
            "type": "string",
            "enum": [
              "asc",
              "desc"
            ]
          }
        }
      }
    },
    "page_number": {
      "type": "integer",
      "description": "1-based page number."
    },
    "offset": {
      "type": "integer",
      "description": "Row offset, alternative to page_number."
    }
  }
}
```

## RapidAPI Example Body (paste into Body tab)
```json
{
  "select": [
    "*"
  ],
  "filter": {
  },
  "order_by": [
    {
      "field": "posted_date",
      "direction": "asc"
    }
  ],
  "page_number": 1
}
```
