# RapidAPI Listing Info — Workbc Jobs

## API Name (short title)
```
Workbc Jobs
```

## Short Description (one-liner shown in search results)
```
Job postings scraped from WorkBC.
```

## Long Description (shown on the API page)
```
WorkBC job listings scraped from the WorkBC results page. Records include job title, company, location, salary range, job type, posting metadata (posted/updated/expires), and listing identifiers.
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
          "description": "Job title (WorkBC listing)"
        },
        "company": {
          "type": "string",
          "description": "Hiring company name"
        },
        "location_raw": {
          "type": "string",
          "description": "Location as shown on WorkBC (e.g., Virtual job based in Penticton, BC)"
        },
        "work_mode": {
          "type": "string",
          "description": "Work mode (Remote, Hybrid, On-site) if provided"
        },
        "salary_raw": {
          "type": "string",
          "description": "Salary string as shown on WorkBC (e.g., $80,000 to $97,000 annually)"
        },
        "job_type": {
          "type": "string",
          "description": "Job type from WorkBC (e.g., Full-time, Permanent)"
        },
        "job_number": {
          "type": "string",
          "description": "WorkBC job number / listing ID"
        },
        "views": {
          "type": "integer",
          "description": "Listing views count"
        },
        "posted_date": {
          "type": "string",
          "description": "Date posted on WorkBC"
        },
        "updated_date": {
          "type": "string",
          "description": "Last updated date on WorkBC"
        },
        "expires_date": {
          "type": "string",
          "description": "Expiry date on WorkBC"
        },
        "url": {
          "type": "string",
          "description": "URL to the WorkBC job posting"
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
    "views": {
      "$gte": 0,
      "$lte": 100
    }
  },
  "order_by": [
    {
      "field": "work_mode",
      "direction": "asc"
    }
  ],
  "page_number": 1
}
```
