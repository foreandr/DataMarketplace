# RapidAPI Listing Info — Upwork Jobs

## API Name (short title)
```
Upwork Jobs
```

## Short Description (one-liner shown in search results)
```
Upwork job feed cards (title, budget, client details, and tags).
```

## Long Description (shown on the API page)
```
Upwork job cards scraped from the search results feed. Records include post age, title, rate/budget details, experience level, description snippet, skills/tags, client verification, client rating/spend, client location, and proposal counts.
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
        "posted_age": {
          "type": "string",
          "description": "Relative posted time (e.g., 'Posted 2 hours ago')"
        },
        "job_type": {
          "type": "string",
          "description": "Hourly or Fixed"
        },
        "experience_level": {
          "type": "string",
          "description": "Experience level (Entry, Intermediate, Expert)"
        },
        "est_time": {
          "type": "string",
          "description": "Estimated project time / hours per week"
        },
        "hourly_rate_min": {
          "type": "number",
          "description": "Minimum hourly rate if shown"
        },
        "hourly_rate_max": {
          "type": "number",
          "description": "Maximum hourly rate if shown"
        },
        "fixed_budget": {
          "type": "number",
          "description": "Fixed-price budget if shown"
        },
        "description": {
          "type": "string",
          "description": "Short description snippet"
        },
        "skills": {
          "type": "string",
          "description": "Comma-separated skills/tags"
        },
        "is_featured": {
          "type": "integer",
          "description": "1 if the job is marked Featured"
        },
        "payment_verified": {
          "type": "integer",
          "description": "1 if client is payment verified"
        },
        "client_rating": {
          "type": "number",
          "description": "Client rating (0-5) if shown"
        },
        "client_spend": {
          "type": "string",
          "description": "Client spend summary (e.g., '$80K+ spent')"
        },
        "client_location": {
          "type": "string",
          "description": "Client location as shown (e.g., United States)"
        },
        "proposals_range": {
          "type": "string",
          "description": "Proposals range (e.g., '20 to 50')"
        },
        "url": {
          "type": "string",
          "description": "URL to the Upwork job post"
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
    "is_featured": {
      "$gte": 0,
      "$lte": 100
    },
    "payment_verified": {
      "$gte": 0
    }
  },
  "order_by": [
    {
      "field": "posted_age",
      "direction": "asc"
    }
  ],
  "page_number": 1
}
```
