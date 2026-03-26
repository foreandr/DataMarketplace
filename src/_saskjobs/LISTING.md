# RapidAPI Listing Info — Saskjobs

## API Name (short title)
```
Saskjobs
```

## Short Description (one-liner shown in search results)
```
Job postings scraped from SaskJobs.
```

## Long Description (shown on the API page)
```
SaskJobs listings scraped from the SaskJobs results page. Records include job title, company, location, NOC code, post date, and listing identifiers.
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
          "description": "Job title (SaskJobs listing)"
        },
        "company": {
          "type": "string",
          "description": "Hiring company name"
        },
        "location_raw": {
          "type": "string",
          "description": "Location as shown on SaskJobs (e.g., Saskatoon, SK)"
        },
        "noc_code": {
          "type": "string",
          "description": "NOC code shown on listing (e.g., NOC 73300)"
        },
        "posted_date": {
          "type": "string",
          "description": "Posting date shown on SaskJobs"
        },
        "job_number": {
          "type": "string",
          "description": "SaskJobs job number / listing ID if available"
        },
        "is_new": {
          "type": "integer",
          "description": "1 if listing is marked as new, else 0"
        },
        "url": {
          "type": "string",
          "description": "URL to the SaskJobs job posting"
        },
        "city": {
          "type": "string",
          "description": "Parsed city"
        },
        "province": {
          "type": "string",
          "description": "Province or state code (e.g., ON, BC)"
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
    "is_new": {
      "$gte": 0,
      "$lte": 100
    }
  },
  "order_by": [
    {
      "field": "noc_code",
      "direction": "asc"
    }
  ],
  "page_number": 1
}
```
