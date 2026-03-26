# RapidAPI Listing Info — Goodwork Jobs

## API Name (short title)
```
Goodwork Jobs
```

## Short Description (one-liner shown in search results)
```
Job postings scraped from GoodWork.
```

## Long Description (shown on the API page)
```
GoodWork listings scraped from the results page. Records include job title, organization, location, work mode, and job type.
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
          "description": "Job title (GoodWork listing)"
        },
        "company": {
          "type": "string",
          "description": "Organization name"
        },
        "location_raw": {
          "type": "string",
          "description": "Location as shown (e.g., Toronto ON, remote, anywhere in Canada)"
        },
        "work_mode": {
          "type": "string",
          "description": "Work mode (Remote, Hybrid, On-site) if present"
        },
        "job_type": {
          "type": "string",
          "description": "Job type (e.g., full-time, contract)"
        },
        "url": {
          "type": "string",
          "description": "URL to the GoodWork job posting"
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
