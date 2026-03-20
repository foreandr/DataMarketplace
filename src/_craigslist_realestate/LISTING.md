# RapidAPI Listing Info — Craigslist Realestate

## API Name (short title)
```
Craigslist Realestate
```

## Short Description (one-liner shown in search results)
```
Craigslist real estate listings with price, beds, baths, and location.
```

## Long Description (shown on the API page)
```
Real estate listings scraped from Craigslist across US & Canadian cities. Records include pricing, bedrooms, bathrooms, square footage when available, listing URL, image, and geo-location data tagged at crawl time. Bedrooms and square footage can be missing for some listings.
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
          "description": "Listing headline"
        },
        "price": {
          "type": "integer",
          "description": "Asking price in USD or CAD"
        },
        "bedrooms": {
          "type": "integer",
          "description": "Number of bedrooms (nullable)"
        },
        "bathrooms": {
          "type": "number",
          "description": "Number of bathrooms (nullable)"
        },
        "square_feet": {
          "type": "integer",
          "description": "Interior size in square feet (nullable)"
        },
        "housing_type": {
          "type": "string",
          "description": "Apartment, house, condo, etc."
        },
        "neighborhood": {
          "type": "string",
          "description": "Neighborhood or area label"
        },
        "posted_date": {
          "type": "string",
          "description": "Posting date as shown on Craigslist"
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
    "price": {
      "$gte": 1000,
      "$lte": 15000
    },
    "bedrooms": {
      "$gte": 0
    }
  },
  "order_by": [
    {
      "field": "price",
      "direction": "asc"
    }
  ],
  "page_number": 1
}
```
