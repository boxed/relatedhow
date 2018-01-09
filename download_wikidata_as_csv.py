from urllib.parse import urlencode

import requests

select = """
SELECT ?item ?parenttaxon ?taxonname ?parenttaxonname WHERE {
  ?item wdt:P225 ?taxonname.
  ?item wdt:P171 ?parenttaxon.
  ?parenttaxon wdt:P225 ?parenttaxonname.
}
"""

result = requests.get('https://query.wikidata.org/sparql?%s' % urlencode([('query', select)]), headers={'Accept': 'text/tab-separated-values'}).text
# print(result)
with open('result.csv', 'w') as f:
    f.write(result)
