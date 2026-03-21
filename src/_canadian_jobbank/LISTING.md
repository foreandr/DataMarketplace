# RapidAPI Listing Info — Canadian Jobbank

## API Name (short title)
```
Canadian Jobbank
```

## Short Description (one-liner shown in search results)
```
Job postings from the Government of Canada Job Bank.
```

## Long Description (shown on the API page)
```
Job listings scraped from the Canadian Job Bank. Records include job title, 
company name, location (city/province), posted date, and salary. 
All salary data is normalized to an hourly rate. Includes tags for 
application types (Direct Apply, LMIA requested, etc.).
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
          "description": "Job title (e.g., Software developer)"
        },
        "company": {
          "type": "string",
          "description": "Hiring company name (e.g., SpaceBridge Inc.)"
        },
        "location_raw": {
          "type": "string",
          "description": "City and Province as shown on listing"
        },
        "posted_date": {
          "type": "string",
          "description": "Date the job was posted"
        },
        "pay": {
          "type": "number",
          "description": "Normalized hourly pay rate (converted from annual if necessary)"
        },
        "is_lmia": {
          "type": "integer",
          "description": "Boolean: 1 if LMIA requested, else 0"
        },
        "is_direct_apply": {
          "type": "integer",
          "description": "Boolean: 1 if Direct Apply is enabled, else 0"
        },
        "url": {
          "type": "string",
          "description": "URL to the job posting"
        },
        "city": {
          "type": "string",
          "description": "Parsed city"
        },
        "state": {
          "type": "string",
          "description": "Province code (e.g., ON, QC, BC)"
        },
        "country": {
          "type": "string",
          "description": "Country (Canada)"
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
    "is_lmia": {
      "$gte": 0,
      "$lte": 100
    },
    "is_direct_apply": {
      "$gte": 0
    },
    "state": {
      "$in": [
        "TX",
        "CA"
      ]
    }
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
