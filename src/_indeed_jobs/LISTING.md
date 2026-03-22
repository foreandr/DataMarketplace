# RapidAPI Listing Info — Indeed Jobs

## API Name (short title)
```
Indeed Jobs
```

## Short Description (one-liner shown in search results)
```
Job postings scraped from Indeed.com.
```

## Long Description (shown on the API page)
```
Job listings scraped from Indeed. Records include job title, company name, location, raw pay string, normalized min/max hourly rate, employment type, schedule tags, benefits, and whether Easy Apply is available.
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
          "description": "Job title (e.g., Software Developer)"
        },
        "company": {
          "type": "string",
          "description": "Hiring company name"
        },
        "location_raw": {
          "type": "string",
          "description": "Location as shown on listing (e.g., North York, ON M2N 6P4)"
        },
        "pay_raw": {
          "type": "string",
          "description": "Pay string as shown (e.g., $24-$26 an hour)"
        },
        "pay_min": {
          "type": "number",
          "description": "Minimum pay normalized to hourly rate"
        },
        "pay_max": {
          "type": "number",
          "description": "Maximum pay normalized to hourly rate"
        },
        "pay_period": {
          "type": "string",
          "description": "Pay period: hour, day, week, month, year"
        },
        "job_type": {
          "type": "string",
          "description": "Employment type: Full-time, Part-time, Contract, etc."
        },
        "schedule": {
          "type": "string",
          "description": "Schedule tags (e.g., Weekends as needed, Flexible schedule)"
        },
        "benefits": {
          "type": "string",
          "description": "Comma-separated benefits (e.g., Vision care, Dental care)"
        },
        "is_easy_apply": {
          "type": "integer",
          "description": "1 if Easy Apply is available, else 0"
        },
        "posted_date": {
          "type": "string",
          "description": "Date posted or relative string (e.g., 2 days ago)"
        },
        "url": {
          "type": "string",
          "description": "URL to the job posting"
        },
        "city": {
          "type": "string",
          "description": "Parsed city"
        },
        "province": {
          "type": "string",
          "description": "Province or state code (e.g., ON, BC, NY)"
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
    "is_easy_apply": {
      "$gte": 0,
      "$lte": 100
    }
  },
  "order_by": [
    {
      "field": "pay_min",
      "direction": "asc"
    }
  ],
  "page_number": 1
}
```
