import requests
from bs4 import BeautifulSoup
import json
import os


def fetch_hs4_codes():
    url = "https://www.censtatd.gov.hk/search/index.php?lang_search=en&l=web&c=HsCode&m=searchChapterA"
    result = []

    for code in range(1, 100):
        fhsCode = f"{code:02d}"
        form_data = {
            'fhsCode': fhsCode,
            'lang_search': 'en',
            'keyword_searched': ''
        }

        response = requests.post(url, data=form_data)
        chapter_a_list = response.json().get('searchChapter', [])

        if not chapter_a_list:
            continue

        hs2_dict = {}
        for index, item in enumerate(chapter_a_list):
            print(f"Processing fhsCode {fhsCode}, item {index + 1} of {len(chapter_a_list)}")

            if len(item['fhsCode']) == 2:
                hs2_dict = {
                    'hs2': item['fhsCode'],
                    'nameE': item['nameE'],
                    'nameC': item['nameC'],
                    'child': []
                }
                result.append(hs2_dict)
            elif len(item['fhsCode']) == 4:
                hs4_dict = {
                    'hs4': item['fhsCode'],
                    'nameE': item['nameE'],
                    'nameC': item['nameC']
                }
                if 'child' in hs2_dict:
                    hs2_dict['child'].append(hs4_dict)


    with open(os.path.join("../data", "hs4_data.json"), 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)

    return result



def fetch_hs8_codes(hs4):
    url = "https://www.censtatd.gov.hk/search/index.php?lang_search=en&l=web&c=HsCode&m=searchChapterB"
    form_data = {
        'fhsCode': hs4,
        'lang_search': 'en',
        'mode': '1'
    }
    response = requests.post(url, data=form_data)
    chapter_b_list = response.json()
    search_chapter = chapter_b_list.get('searchChapter', [])
    hs8_list = [
        {
            'fhsCode': item['fhsCode'],
            'nameE': item['nameE'],
            'nameC': item['nameC']
        }
        for item in search_chapter if len(item['fhsCode']) == 8
    ]
    return hs8_list




if __name__ == "__main__":

    hs4_data = fetch_hs4_codes()
    print(hs4_data)

    hs4 = '1701'
    hs8_data = fetch_hs8_codes(hs4)
    print(hs8_data)




