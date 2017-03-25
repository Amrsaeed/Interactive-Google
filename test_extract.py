from goose import Goose
import json
from requests import get
import tldextract
import logging

query = 'batman'
resultCursor = 1

SITE = 'https://www.googleapis.com/customsearch/v1?key=AIzaSyAyaR2yyP3RETDJh5MlLP7ZEU7cFe5QvbA&cx=000510991857172859853:np4wq9ylzrq&q=' + \
           query + '&start=' + str(resultCursor) + '&num=1'
response = get(SITE)
json_data = json.loads(response.text)

print(json_data['items'][resultCursor-1]['title'])
print(json_data['items'][resultCursor-1]['link'])

ext = tldextract.extract(json_data['items'][resultCursor-1]['link'])
print(ext.domain)