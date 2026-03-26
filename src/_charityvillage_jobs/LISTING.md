# RapidAPI Listing Info — Charityvillage Jobs

## API Name (short title)
```
Charityvillage Jobs
```

## Short Description (one-liner shown in search results)
```
Job postings scraped from CharityVillage.
```

## Long Description (shown on the API page)
```
CharityVillage listings scraped from the results page. Records include job title, organization, location, work mode, job type, salary, posted/expiry dates, and quick-apply availability.
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
          "description": "Job title (CharityVillage listing)"
        },
        "company": {
          "type": "string",
          "description": "Organization name"
        },
        "location_raw": {
          "type": "string",
          "description": "Location as shown (e.g., Vancouver, BC, Canada)"
        },
        "work_mode": {
          "type": "string",
          "description": "Work mode (Onsite, Fully Remote, Hybrid)"
        },
        "job_type": {
          "type": "string",
          "description": "Job type (Full Time, Part Time, Contract)"
        },
        "salary_raw": {
          "type": "string",
          "description": "Salary string as shown (e.g., $50,000 - $60,000 per year)"
        },
        "posted_date": {
          "type": "string",
          "description": "Posted date shown on listing"
        },
        "expires_date": {
          "type": "string",
          "description": "Expiry date shown on listing"
        },
        "is_quick_apply": {
          "type": "integer",
          "description": "1 if Quick Apply is available, else 0"
        },
        "url": {
          "type": "string",
          "description": "URL to the CharityVillage job posting"
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
    "is_quick_apply": {
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
