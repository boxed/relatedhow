from wikidataintegrator import wdi_login
from wikidataintegrator.wdi_core import *

login_instance = wdi_login.WDLogin(user='boxed', pwd='AGhNZpHGiottAKChhwXAwUCYYvyDE7HJbCKRzFjop3qDaxDcJu')

with open('no_parent_taxons.txt') as f:
    x = f.read()

for line in x.split('\n'):
    id = 'Q%s' % line
    try:
        to_update = WDItemEngine(wd_item_id=id)
    except (KeyError, IndexError):
        continue

    if 'P31' not in to_update.get_property_list():
        # this doesn't even have an "instance of" definition, skip it
        continue

    try:
        if to_update.get_wd_json_representation()['claims']['P31'][0]['mainsnak']['datavalue']['value']['id'] != 'Q16521':
            # not a taxon
            print('%s: not a taxon' % id)
            continue
    except (KeyError, IndexError):
        print('%s: really not a taxon' % id)
        continue

    name = to_update.get_label()

    if ' x ' in name:
        name = name.replace(' x ', ' ')
    parent_name = name.rpartition(' ')[0]

    if ' ' not in name:
        print('%s: no space in the name' % id)
        continue

    parent_search_result = [x for x in WDItemEngine.get_wd_search_results(parent_name) if x != id]
    if not parent_search_result:
        print("%s: didn't find a parent" % id)
        continue
    try:
        parent_taxon = WDItemEngine(wd_item_id=parent_search_result[0])
    except KeyError:
        print("%s: didn't find a parent (2)" % id)
        continue

    # TODO: Check that there is no parent taxon already. This can happen if our data is out of date.

    if 'taxon' in parent_taxon.get_description() or 'genus' in parent_taxon.get_description() or 'species' in parent_taxon.get_description():
        to_update.update([WDItemID(prop_nr='P171', value=parent_search_result[0])])
        if to_update.get_label().replace(' x ', ' ').rpartition(' ')[0] == parent_taxon.get_label():
            print(id, to_update.get_label(), '(%s)' % to_update.get_description(), '<-',
                  parent_search_result[0], parent_taxon.get_label(), '(%s)' % parent_taxon.get_description())
            to_update.write(login_instance)
        else:
            print("%s: didn't look right, skipping" % id)
    else:
        print('found %s (%s) for %s, which does not look right, skipping it' % (parent_taxon.get_label(), parent_taxon.get_description(), id))
        

# x = WDItemEngine(wd_item_id='Q13050791')
# WDItemEngine.get_wd_search_results('Salmo ischchan')
# Out[11]: ['Q2416197', 'Q13050791']
# x.update([WDItemID(prop_nr='P171', value='Q737838')])
# x.write()
