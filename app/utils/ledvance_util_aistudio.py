import requests
import time
import hashlib
import hmac
import json
from datetime import date, timedelta

# --- 1. CONFIGURATION: ENTER YOUR DETAILS HERE ---
ACCESS_ID = ""
ACCESS_KEY = ""
API_ENDPOINT = "https://openapi.tuyaeu.com" # Change to your region
DEVICE_ID = "33788026500291061724"

# The standard DP code for energy consumption.
# You can verify this by calling get_device_functions().
ENERGY_DP_CODE = "add_ele"

class TuyaAPI:
    """A class to interact with the Tuya v1.0 API, now with statistics methods."""

    def __init__(self, access_id: str, access_key: str, endpoint: str):
        self.access_id = access_id
        self.access_key = access_key
        self.endpoint = endpoint
        self.session = requests.Session()

    def _calculate_sign(self, method: str, path: str, params: dict = None, body: dict = None) -> tuple:
        """Calculates the HMAC-SHA256 signature required for Tuya API calls."""
        t = int(time.time() * 1000)
        body_str = json.dumps(body, separators=(',', ':')) if body else ""
        body_hash_str = hashlib.sha256(body_str.encode('utf-8')).hexdigest()
        
        query_str = ""
        if params:
            sorted_params = sorted(params.items())
            query_str = "&".join([f"{k}={v}" for k, v in sorted_params])
        
        path_with_query = path
        if query_str:
            path_with_query += "?" + query_str
            
        string_to_sign = f"{method}\n{body_hash_str}\n\n{path_with_query}"
        message = self.access_id + str(t) + string_to_sign
        
        sign = hmac.new(
            self.access_key.encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest().upper()
        
        headers = {
            "client_id": self.access_id,
            "sign": sign,
            "t": str(t),
            "sign_method": "HMAC-SHA256",
            "Content-Type": "application/json"
        }
        return headers

    def _make_request(self, method: str, path: str, params: dict = None, body: dict = None):
        """Makes a signed request to the Tuya API."""
        headers = self._calculate_sign(method, path, params, body)
        url = self.endpoint + path
        
        try:
            response = self.session.request(method, url, params=params, json=body, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {url}: {e}")
            if e.response:
                print(f"Response Body: {e.response.text}")
            return None

    def get_device_functions(self, device_id: str):
        """Fetches the list of functions (DPs) a device supports."""
        print(f"[*] Discovering Data Points (DPs) for device {device_id}...")
        path = f"/v1.0/devices/{device_id}/functions"
        return self._make_request("GET", path)

    def get_total_consumption(self, device_id: str, code: str):
        """Fetches the all-time total consumption for a specific DP code."""
        print(f"\n[*] Fetching TOTAL consumption for DP code '{code}'...")
        path = f"/v1.0/devices/{device_id}/statistics/total"
        params = {'code': code}
        return self._make_request("GET", path, params=params)

    def get_daily_consumption(self, device_id: str, code: str, start_day: str, end_day: str):
        """Fetches daily consumption for a date range (format: YYYYMMDD)."""
        print(f"\n[*] Fetching DAILY consumption for '{code}' from {start_day} to {end_day}...")
        path = f"/v1.0/devices/{device_id}/statistics/days"
        params = {'code': code, 'start_day': start_day, 'end_day': end_day}
        return self._make_request("GET", path, params=params)

    def get_monthly_consumption(self, device_id: str, code: str, start_month: str, end_month: str):
        """Fetches monthly consumption for a date range (format: YYYYMM)."""
        print(f"\n[*] Fetching MONTHLY consumption for '{code}' from {start_month} to {end_month}...")
        path = f"/v1.0/devices/{device_id}/statistics/months"
        params = {'code': code, 'start_month': start_month, 'end_month': end_month}
        return self._make_request("GET", path, params=params)

def display_consumption_data(result: dict, data_type: str):
    """Parses and displays consumption data in a readable format."""
    if not result or not result.get("success"):
        print(f"Failed to get {data_type} data or the result was unsuccessful.")
        if result and result.get('msg'):
            print(f"  > API Message: {result['msg']}")
        return

    res = result.get('result', {})
    
    # The value for 'add_ele' is typically in 0.01 kWh. Divide by 100.
    # For some devices, it might be Wh. In that case, divide by 1000.
    # We will assume 0.01 kWh as it's common for plugs.
    divisor = 100.0
    
    if data_type == 'total':
        value_kwh = res.get('value', 0) / divisor
        print(f"  - Total Consumption: {value_kwh:.2f} kWh")
    
    elif data_type == 'daily':
        print("  --- Daily Breakdown ---")
        stats = res.get('d_stat', {})
        if not stats:
            print("  No daily data available for this period.")
            return
        for day, value in sorted(stats.items()):
            value_kwh = value / divisor
            print(f"    - {day[:4]}-{day[4:6]}-{day[6:]}: {value_kwh:.3f} kWh")
            
    elif data_type == 'monthly':
        print("  --- Monthly Breakdown ---")
        stats = res.get('m_stat', {})
        if not stats:
            print("  No monthly data available for this period.")
            return
        for month, value in sorted(stats.items()):
            value_kwh = value / divisor
            print(f"    - {month[:4]}-{month[4:]}: {value_kwh:.2f} kWh")
    
    print("-" * 20)


if __name__ == "__main__":
    if "YOUR_ACCESS_ID" in ACCESS_ID or "YOUR_ACCESS_KEY" in ACCESS_KEY:
        print("ERROR: Please fill in your ACCESS_ID and ACCESS_KEY in the script.")
    else:
        api_client = TuyaAPI(ACCESS_ID, ACCESS_KEY, API_ENDPOINT)
        
        # Optional: Verify the DP code is correct for your device
        # functions = api_client.get_device_functions(DEVICE_ID)
        # if functions: print(json.dumps(functions, indent=2))
        
        # 1. Get TOTAL consumption
        total_data = api_client.get_total_consumption(DEVICE_ID, ENERGY_DP_CODE)
        display_consumption_data(total_data, 'total')

        # 2. Get DAILY consumption for the last 7 days
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        daily_data = api_client.get_daily_consumption(
            DEVICE_ID,
            ENERGY_DP_CODE,
            start_date.strftime('%Y%m%d'),
            end_date.strftime('%Y%m%d')
        )
        display_consumption_data(daily_data, 'daily')
        
        # 3. Get MONTHLY consumption for the last 3 months
        # Note: The API might have limits on how far back you can query.
        current_month = date.today().strftime('%Y%m')
        three_months_ago = (date.today().replace(day=1) - timedelta(days=62)).strftime('%Y%m')
        monthly_data = api_client.get_monthly_consumption(
            DEVICE_ID,
            ENERGY_DP_CODE,
            three_months_ago,
            current_month
        )
        display_consumption_data(monthly_data, 'monthly')