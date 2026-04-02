import requests

API_KEY = "579b464db66ec23bdd00000139c70e91ad414a1540050651fe84fb25"
URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

def test_mandi(crop, district=""):
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 5,
        "filters[commodity]": crop.title(),
    }

    # add district only if provided
    if district:
        params["filters[district]"] = district

    try:
        response = requests.get(URL, params=params, timeout=10)
        print("Status Code:", response.status_code)

        data = response.json()
        records = data.get("records", [])

        print("Number of records:", len(records))

        for r in records:
            print("----------------------------")
            print("Market:", r.get("market"))
            print("District:", r.get("district"))
            print("Commodity:", r.get("commodity"))
            print("Min Price:", r.get("min_price"))
            print("Max Price:", r.get("max_price"))
            print("Modal Price:", r.get("modal_price"))

        return records

    except Exception as e:
        print("Error:", e)
        return []


if __name__ == "__main__":
    prices = test_mandi("Rice", "kadapa")   # ✅ correct usage
    print("Returned:", prices)