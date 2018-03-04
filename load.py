import pickle

# with open('taxon_by_pk.pickle', 'rb') as f:
#     result = pickle.load(f)
from datetime import datetime

with open('data.pickle', 'rb') as f:
    result = pickle.load(f)

name_by_pk = {}
for name, pks in result['names'].items():
    for pk in pks:
        name_by_pk[pk] = name

start = datetime.now()
h = list(result['english_names']['Human'])[0]
while h:
    print(name_by_pk.get(h), h)
    h = result['parents'].get(h)

print(datetime.now() - start)

# input('press')
