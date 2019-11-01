from urllib.request import urlopen
import gzip
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open('taxon_data.json', 'wb') as out:
    with urlopen('https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.gz', context=ctx) as f:
        with gzip.open(f) as f2:
            for line in f2:
                if b'"P171"' in line or b'"Q16521"' in line:
                    out.write(line)

