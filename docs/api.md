# API Reference

The app exposes a single HTTP endpoint that any authorized system can call to get a live shipping rate.

---

## Endpoint

```
POST /api/method/shipping_integration.api.get_rates
```

---

## Authentication

Every request must include the pre-shared API key in the `X-Shipping-Key` header. The key is configured in **Shipping Integration Settings → QTSI API Key**.

```
X-Shipping-Key: <your-api-key>
```

If the header is missing, empty, or does not match the stored key, the endpoint returns **401 Unauthorized**.

If the `qtsi_api_key` field in Settings is not configured, the endpoint refuses all requests — it will never fall open.

---

## Request

**Headers:**

| Header | Required | Value |
|---|---|---|
| `Content-Type` | Yes | `application/json` |
| `X-Shipping-Key` | Yes | Pre-shared API key |

**Body:**

```json
{
  "items": [
    {
      "item_code": "ITEM-001",
      "qty": 2,
      "weight_kg": 1.5,
      "width_cm": 30,
      "height_cm": 20,
      "depth_cm": 15
    }
  ],
  "destination": {
    "street": "123 Main St",
    "city": "Toronto",
    "province": "ON",
    "postal_code": "M5H 2N2",
    "country": "CA"
  }
}
```

### `items` array

| Field | Type | Required | Description |
|---|---|---|---|
| `item_code` | string | Yes | ERPNext Item code (used to look up Preferred Supplier) |
| `qty` | number | Yes | Quantity |
| `weight_kg` | number | No | Package weight in kg. Defaults to `1.0` if omitted |
| `width_cm` | number | No | Package width in cm. Defaults to `20` if omitted |
| `height_cm` | number | No | Package height in cm. Defaults to `10` if omitted |
| `depth_cm` | number | No | Package depth (length) in cm. Defaults to `20` if omitted |

### `destination` object

| Field | Type | Required | Description |
|---|---|---|---|
| `street` | string | Yes | Delivery street address |
| `city` | string | Yes | City |
| `province` | string | Yes | Province / state code (e.g. `ON`, `BC`) |
| `postal_code` | string | Yes | Postal code (e.g. `M5H 2N2`) |
| `country` | string | No | ISO country code. Defaults to `CA` |

---

## Response

### Success — `200 OK`

Frappe wraps all responses in a `message` key:

```json
{
  "message": {
    "rate": 24.50,
    "currency": "CAD"
  }
}
```

| Field | Type | Description |
|---|---|---|
| `rate` | number | Total shipping cost rounded to 2 decimal places |
| `currency` | string | Always `"CAD"` |

### Error Responses

| Status | Cause |
|---|---|
| `401 Unauthorized` | Missing, invalid, or unconfigured `X-Shipping-Key` |
| `400 Bad Request` | Missing `items` or `destination`, or malformed JSON |
| `500 Internal Server Error` | eShipper API unreachable or returned an unexpected response |

Frappe error responses follow this shape:

```json
{
  "exc_type": "AuthenticationError",
  "exception": "AuthenticationError: Unauthorized"
}
```

---

## curl Example

```bash
curl -X POST "https://<your-erp>/api/method/shipping_integration.api.get_rates" \
  -H "Content-Type: application/json" \
  -H "X-Shipping-Key: your-secret-key-here" \
  -d '{
    "items": [
      { "item_code": "ROUTER-001", "qty": 1, "weight_kg": 2.0 }
    ],
    "destination": {
      "street": "456 King St W",
      "city": "Toronto",
      "province": "ON",
      "postal_code": "M5V 1M3",
      "country": "CA"
    }
  }'
```

---

## Rate Aggregation Behavior

When items originate from multiple warehouses (based on Supplier Warehouse Map), the endpoint calculates a rate for each origin separately and sums them:

```
total_rate = sum(
  average(eShipper rates for group)
  for each origin group
)
```

If eShipper returns no rates for a group, the group is skipped and the omission is logged to Frappe's Error Log. The caller receives whatever partial total was calculated — review error logs if rates seem lower than expected.

---

## Integration Notes

- **No persistent state** — each request is stateless; eShipper tokens are cached transparently in Redis.
- **Dimensions are optional** — if your system doesn't track dimensions, omit them. eShipper will use the configured defaults (1 kg, 20×10×20 cm). Actual rates may differ from real dimensions.
- **Rate is advisory** — the returned rate is an estimate based on carrier quotes at time of request. Actual billed amount may vary.
