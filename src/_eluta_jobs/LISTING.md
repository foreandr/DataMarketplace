# RapidAPI Listing Info — Eluta Jobs

## API Name (short title)
```
Eluta Jobs
```

## Short Description (one-liner shown in search results)
```
Job postings scraped from Eluta.
```

## Long Description (shown on the API page)
```
Eluta listings scraped from the Eluta results page. Records include job title, company, location, remote/work mode, posting age, and summary text.
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
          "description": "Job title (Eluta listing)"
        },
        "company": {
          "type": "string",
          "description": "Hiring company name"
        },
        "location_raw": {
          "type": "string",
          "description": "Location as shown on Eluta (e.g., London ON - Work Remotely)"
        },
        "work_mode": {
          "type": "string",
          "description": "Work mode (Remote/Hybrid/On-site) if shown"
        },
        "summary": {
          "type": "string",
          "description": "Listing summary snippet"
        },
        "posted_relative": {
          "type": "string",
          "description": "Relative posted time (e.g., 9 minutes ago)"
        },
        "url": {
          "type": "string",
          "description": "URL to the Eluta job posting"
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
  "filter": {},
  "order_by": [
    {
      "field": "work_mode",
      "direction": "asc"
    }
  ],
  "page_number": 1
}
```
