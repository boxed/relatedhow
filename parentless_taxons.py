# to run this, rename __x to x and replace the contents of the string to something useful

__x = """Stauropus dentilinea 55633933
Steere Herbarium ID 6035
Stegopodus 7606708
Steinernema xueshanense 56274323
Stellantchasmus 55633946
Stellaria alatavica 58814092
Stenakron 48968748
Stenobothrini 49001003
Stenochidus cyanescens 63243204
Stenotus borealis 59422958
Stephanomeria occultata 55633966
Stephenospongia 7610938
Steppe grey shrike 48968378
Sterculia campanulata 59264301
"""

from wikidataintegrator import wdi_login
from wikidataintegrator.wdi_core import *

login_instance = wdi_login.WDLogin(user='boxed', pwd='AGhNZpHGiottAKChhwXAwUCYYvyDE7HJbCKRzFjop3qDaxDcJu')

for line in x.split('\n'):
    rest, _, id = line.rpartition(' ')
    id = 'Q%s' % id
    if rest.count(' ') == 2:
        parent_name = rest.rpartition(' ')[0]
        try:
            to_update = WDItemEngine(wd_item_id=id)
        except KeyError:
            continue
        parent_search_result = [x for x in WDItemEngine.get_wd_search_results(parent_name) if x != id]
        if not parent_search_result:
            continue
        parent_taxon = WDItemEngine(wd_item_id=parent_search_result[0])
        to_update.update([WDItemID(prop_nr='P171', value=parent_search_result[0])])
        if to_update.get_label().rpartition(' ')[0] == parent_taxon.get_label():
            print(id, to_update.get_label(), '(%s)' % to_update.get_description(), '<-', 
                  parent_search_result[0], parent_taxon.get_label(), '(%s)' % parent_taxon.get_description())
            to_update.write(login_instance)
        

# x = WDItemEngine(wd_item_id='Q13050791')
# WDItemEngine.get_wd_search_results('Salmo ischchan')
# Out[11]: ['Q2416197', 'Q13050791']
# x.update([WDItemID(prop_nr='P171', value='Q737838')])
# x.write()
