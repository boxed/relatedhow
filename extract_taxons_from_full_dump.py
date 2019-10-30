# import bz2
#
# buffer = b''
# c = 0
# n = 0
# limit = 100 * 1024 * 1024
# # with open('taxon_data.json', 'wb') as out:
# with bz2.open('latest-all.json.bz2') as f:
#     while True:
#         l = f.readline()
#         n += len(l)
#         if n > limit:
#             break
#         # if b'taxon' in l:
#         #     break
#             # c += 1
#             # if c >= 100:
#             #     exit(1)
#         # out.write(l)

from urllib.request import urlopen
import gzip

with open('taxon_data.json', 'wb') as out:
    with urlopen('https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.gz') as f:
        with gzip.open(f) as f2:
            for line in f2:
                if b'"P171"' in line or b'"Q16521"' in line:
                    out.write(line)

