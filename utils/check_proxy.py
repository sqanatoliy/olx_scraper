import requests

proxies = {
    "http": "http://n8DJ9JNKYsFy:K8HXRFSk3Vp8_country-ua@superproxy.zenrows.com:1338",
    "https": "https://n8DJ9JNKYsFy:K8HXRFSk3Vp8_country-ua@superproxy.zenrows.com:1338",
}

if __name__ == "__main__":
    try:
        response = requests.get("https://httpbin.org/ip", timeout=30, proxies=proxies)
        print("Proxy Response:", response.json())
    except Exception as e:
        print("Proxy Error:", e)
