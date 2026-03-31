# RapidAPI Listing Info — Jobspider Jobs

## API Name (short title)
```
Jobspider Jobs
```

## Short Description (one-liner shown in search results)
```
Job postings scraped from JobSpider.
```

## Long Description (shown on the API page)
```
JobSpider listings scraped from the results page. Records include job title, company, location, category, posted date, and sponsored flag.
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
          "description": "Job title"
        },
        "company": {
          "type": "string",
          "description": "Company or organization name"
        },
        "location_raw": {
          "type": "string",
          "description": "Location as shown (e.g., Juneau, AK)"
        },
        "category": {
          "type": "string",
          "description": "Job category (e.g., General, Building Trades/Construction)"
        },
        "posted_date": {
          "type": "string",
          "description": "Date the listing was added (e.g., 3/31/2026 1:24:21 PM PST)"
        },
        "is_sponsored": {
          "type": "integer",
          "description": "1 if the listing is sponsored/promoted, else 0"
        },
        "description": {
          "type": "string",
          "description": "Short description snippet from the listing"
        },
        "url": {
          "type": "string",
          "description": "URL to the JobSpider job posting"
        },
        "city": {
          "type": "string",
          "description": "Parsed city"
        },
        "province": {
          "type": "string",
          "description": "State or province code (e.g., AK, ON)"
        },
        "country": {
          "type": "string",
          "description": "Country"
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
    "is_sponsored": {
      "$gte": 0,
      "$lte": 100
    }
  },
  "order_by": [
    {
      "field": "category",
      "direction": "asc"
    }
  ],
  "page_number": 1
}
```
