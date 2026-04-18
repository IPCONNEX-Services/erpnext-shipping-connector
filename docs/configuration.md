# Configuration Reference

All settings live in a single ERPNext document: **Shipping Integration Settings**.

Navigate there via the ERPNext search bar or:  
`https://<your-erp>/app/shipping-integration-settings`

---

## eShipper API Credentials

These are required for the app to fetch rates from eShipper.

### `eshipper_api_url`
**Type:** Data | **Required:** Yes

Base URL of the eShipper API. Do not include a trailing slash.

```
https://api.eshipper.com
```

> Find this in the eShipper portal under **Account → API Access → Base URL**.

### `eshipper_client_id`
**Type:** Data | **Required:** Yes

The OAuth2 client ID for your eShipper account.

> Found in the eShipper portal under **Account → API Access → Client ID**.

### `eshipper_client_secret`
**Type:** Password | **Required:** Yes

The OAuth2 client secret. Stored encrypted in the database — never returned in plain text via the API.

> Found in the eShipper portal under **Account → API Access → Client Secret**.

**Token caching:** After a successful OAuth2 handshake, the access token is cached in Frappe's Redis cache for `expires_in - 60` seconds (minimum 60 seconds). Subsequent rate requests reuse the cached token until it nears expiry.

---

## QTSI API Key

### `qtsi_api_key`
**Type:** Password | **Required:** Yes (endpoint refuses all requests if unset)

A secret shared between this app and the calling system (e.g. QTSI Store). The caller sends it in the `X-Shipping-Key` HTTP header.

**Generating a key:**
```bash
openssl rand -hex 32
```

**Security:** The key is compared using `hmac.compare_digest()` — constant-time comparison that prevents timing attacks. If the field is empty, the endpoint refuses all requests with `AuthenticationError` (fail-closed).

---

## Default Origin Warehouse

The fallback pickup address used when an item's supplier has no entry in the Supplier Warehouse Map.

### `default_origin_street`
**Type:** Data | **Required:** Yes

Street address of the default IPCONNEX warehouse. Example: `1234 Logistics Blvd`

### `default_origin_city`
**Type:** Data | **Required:** Yes

City. Example: `Montreal`

### `default_origin_province`
**Type:** Data | **Required:** Yes

Province or state code. Example: `QC`

### `default_origin_postal`
**Type:** Data | **Required:** Yes

Postal code. Example: `H3B 1A7`

### `default_origin_country`
**Type:** Data | **Required:** No | **Default:** `CA`

ISO 3166-1 alpha-2 country code. Leave as `CA` for Canada.

---

## Supplier Warehouse Map

**Type:** Child table (one row per supplier)

Maps a Frappe **Supplier** to a specific warehouse pickup address. When the app groups items by origin, it looks up each item's **Preferred Supplier** field (on the Item DocType) and checks this table. If a match is found, the supplier's warehouse address is used as the origin; otherwise the default origin is used.

### When to use

Add a row for every supplier that ships directly from their own warehouse rather than through your default facility. This enables accurate multi-origin rate calculation.

### Fields per row

| Field | Type | Required | Description |
|---|---|---|---|
| `supplier` | Link → Supplier | Yes | The Frappe Supplier record |
| `street` | Data | Yes | Warehouse street address |
| `city` | Data | Yes | City |
| `province` | Data | Yes | Province / state code |
| `postal_code` | Data | Yes | Postal code |
| `country` | Data | No | ISO country code, defaults to `CA` |

### Example

| Supplier | Street | City | Province | Postal Code | Country |
|---|---|---|---|---|---|
| Acme Networking | 500 Industrial Way | Mississauga | ON | L5T 1A9 | CA |
| GlobalTech Supply | 12 Port Rd | Vancouver | BC | V6C 3E1 | CA |

Items whose Preferred Supplier is **Acme Networking** will be shipped from Mississauga; items from **GlobalTech Supply** from Vancouver. Any other items use the default origin warehouse.

---

## Post-Configuration Checklist

- [ ] eShipper API URL set and reachable
- [ ] eShipper Client ID + Secret saved
- [ ] QTSI API Key generated and shared with calling system
- [ ] Default origin warehouse address complete
- [ ] Supplier Warehouse Map rows added for all direct-ship suppliers
- [ ] Test a rate request (see [api.md](api.md))
