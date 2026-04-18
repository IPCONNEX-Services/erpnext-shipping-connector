# Integration: QTSI Store

**Repo:** [IPCONNEX-Services/QTSI-Store](https://github.com/IPCONNEX-Services/QTSI-Store)

QTSI Store is a Next.js storefront that calls `erpnext-shipping-connector` during checkout to display live shipping costs. The integration is entirely on the QTSI side — no QTSI-specific code exists in this app.

---

## Architecture

```
QTSI Storefront (Next.js)
        │
        │ reads config (URL + key)
        ▼
QTSI ERPNext — Shipping Config (Single DocType)
        │
        │ POST /api/method/shipping_integration.api.get_rates
        │ X-Shipping-Key: <caller_api_key>
        ▼
IPCONNEX ERPNext — erpnext-shipping-connector
        │
        ▼
    eShipper API
```

---

## QTSI-Side Components

### 1. Shipping Config DocType (QTSI ERPNext)

A custom Single DocType in QTSI's ERPNext instance that stores the connection details:

| Field | Description |
|---|---|
| `ipconnex_erp_url` | Base URL of the IPCONNEX ERP instance |
| `ipconnex_shipping_key` | The `caller_api_key` value from IPCONNEX Shipping Integration Settings |

Navigate to it at: `https://<qtsi-erp>/app/shipping-config`

### 2. `getShippingConfig()` (Next.js)

Located in `frontend/src/lib/erpnext.ts`. Reads the Shipping Config DocType from QTSI ERPNext via REST API. Cached by Next.js for 5 minutes (`revalidate: 300`).

```typescript
export async function getShippingConfig(): Promise<{ url: string; key: string } | null>
```

### 3. `getShippingRates()` (Next.js)

Located in `frontend/src/lib/shipping.ts`. A Next.js Server Action that:
1. Calls `getShippingConfig()` to get the endpoint URL and key
2. POSTs to `erpnext-shipping-connector` with cart items and the checkout address
3. Returns `{ rate, currency }` or `{ error }` on failure

### 4. CheckoutView (React)

Located in `frontend/src/app/checkout/CheckoutView.tsx`. Calls `getShippingRates()` with an 800ms debounce as the user fills in their address. Falls back to CAD $50 if the shipping service is unavailable.

---

## Setup Checklist

- [ ] `erpnext-shipping-connector` installed on IPCONNEX ERP
- [ ] IPCONNEX generates a `caller_api_key` in Shipping Integration Settings
- [ ] IPCONNEX shares the ERP base URL + key with QTSI
- [ ] QTSI fills in **Shipping Config** in their ERPNext instance
- [ ] QTSI deploys the Next.js frontend
- [ ] Smoke test: fill a checkout address on the QTSI storefront and verify a live rate appears
