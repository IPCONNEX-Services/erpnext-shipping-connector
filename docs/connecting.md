# Connecting an External System

`erpnext-shipping-connector` is a generic shipping rate service. Any system that can make HTTP POST requests can integrate with it by following this pattern.

---

## What the Connector Needs From You

| Item | Description |
|---|---|
| Endpoint URL | `https://<your-erp>/api/method/shipping_integration.api.get_rates` |
| Caller API Key | The value you set in **Shipping Integration Settings → Caller API Key** |

---

## Integration Steps

### 1. Generate a Caller API Key

On the IPCONNEX ERP instance where `shipping_integration` is installed:

1. Open **Shipping Integration Settings**
2. Generate a key: `openssl rand -hex 32`
3. Paste it into **Caller API Key** and save

### 2. Share the Key and Endpoint URL

Provide the calling system with:
- The ERP base URL (e.g. `https://erp.ipconnex.com`)
- The generated API key

### 3. Calling System Stores the Config

The calling system should store these two values securely (environment variables, an encrypted settings record, etc.) and attach them to every request.

### 4. Make a Rate Request

```bash
POST https://<erp-host>/api/method/shipping_integration.api.get_rates
X-Shipping-Key: <caller-api-key>
Content-Type: application/json

{
  "items": [...],
  "destination": {...}
}
```

See [api.md](api.md) for the full request/response schema.

---

## Example Integrations

Integrations are implemented entirely on the calling system's side. See [api.md](api.md) for the request/response contract any system must implement.
