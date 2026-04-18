app_name = "shipping_integration"
app_title = "Shipping Integration"
app_publisher = "IPCONNEX"
app_description = "eShipper rate calculation for IPCONNEX"
app_email = "dev@ipconnex.com"
app_license = "MIT"
required_apps = ["erpnext"]

fixtures = [
    {"dt": "DocType", "filters": [["module", "=", "Shipping Integration"]]}
]
