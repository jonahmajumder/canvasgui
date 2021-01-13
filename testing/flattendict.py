import json
from types import SimpleNamespace

def flat_dict(elem, parentkey='', joinchar='_'):  
    newelems = {}
    if isinstance(elem, dict):
        for (k,v) in elem.items():
            fullkey = joinchar.join([parentkey, k]) if len(parentkey) > 0 else k
            newelems.update(flat_dict(v, fullkey))
    elif isinstance(elem, (list, tuple)):
        for (i, v) in enumerate(elem):
            fullkey = parentkey + str(i)
            newelems.update(flat_dict(v, fullkey))
    else:
        newelems.update({parentkey: elem})

    return newelems

def objectify(item):  
    if isinstance(item, dict):
        newitems = {k:objectify(v) for (k,v) in item.items()}
        return SimpleNamespace(**newitems)
    elif isinstance(item, (list, tuple)):
        return [objectify(v) for v in item]
    else:
        return item