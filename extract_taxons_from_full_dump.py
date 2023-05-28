from urllib.request import urlopen
import gzip
import ssl

# ctx = ssl.create_default_context()
# ctx.check_hostname = False
# ctx.verify_mode = ssl.CERT_NONE
with open('taxon_data.json', 'wb') as out:
    # with open('/Users/boxed/Downloads/wikidata-20220103-all.json.gz', 'w') as f:
    # with urlopen('https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.gz', context=ctx) as f:
    with gzip.open('/Users/boxed/Downloads/wikidata-20220103-all.json.gz') as f2:
        for line in f2:
            # print(line)
            if b'"P171"' in line or b'"Q16521"' in line or b'"Q55983715"' in line or b'"P1843"' in line:
                out.write(line)
