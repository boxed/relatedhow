x = """"""


from wikidataintegrator import wdi_login
from wikidataintegrator.wdi_core import *
from subprocess import call

login_instance = wdi_login.WDLogin(user='boxed', pwd='AGhNZpHGiottAKChhwXAwUCYYvyDE7HJbCKRzFjop3qDaxDcJu')


for id in x.split('\n'):
    try:
        to_update = WDItemEngine(wd_item_id=id)
    except (KeyError, IndexError):
        continue

    call('open https://www.wikidata.org/wiki/%s' % id, shell=True)
    parent_id = input('parent of %s: ' % id).strip()
    if not parent_id:
        continue
    if not parent_id.startswith('Q'):
        try:
            parent_search_result = [x for x in WDItemEngine.get_wd_search_results(parent_id) if x != id]
        except KeyError:
            continue
        if not parent_search_result:
            print("    no search match")
            continue
        parent_id = parent_search_result[0]    
        parent_taxon = WDItemEngine(wd_item_id=parent_id)
        print('    ', parent_taxon.get_label(), parent_taxon.get_description())
    if not parent_id.startswith('Q'):
        print('   skipped')
        continue
    to_update.update([WDItemID(prop_nr='P171', value=parent_id)])
    to_update.write(login_instance)
    