import requests

LEPINGUD = {
    'S9a': '2801667',
    'K19': '1644020',
}

# BASE_URL = 'https://www.keskkonnateenused.ee/customer-support/next-shipping-day?contractNumber='
API_URL = "https://cms.keskkonnateenused.ee/wp-json/general-purpose-api/upcoming-discharges"
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
# hangib Keskkonnateenuse veebist järgmise veopäeva
def get_next_servicedata(leping):
    payload = {'contractNumber': leping}
    r = requests.get(API_URL, params=payload)
    if r.status_code == 200:
        return r.json()
    else:
        return None
    

if __name__ == "__main__":
    for aadress in LEPINGUD.keys():
        leping = LEPINGUD[aadress]
        data = get_next_servicedata(leping)
        if data:
            for tyhjendus in data:
                print(aadress, tyhjendus['date'], tyhjendus['garbage'], tyhjendus['itemType'])