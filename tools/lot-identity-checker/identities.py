"""Resolve declared aliases to canonical lots without merging or duplicating stock."""
import toolkit as t
import material_core as c

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','lots','aliases'})
    t.require(value['format']=='outlands-lot-identities-v1','FORMAT_INVALID')
    lots,lc,issues=c.rows(value['lots'],c.lot,'lots');aliases,ac,other=c.rows(value['aliases'],c.alias,'aliases');issues+=other
    resolved=c.resolve(lots,aliases,issues);identities=totals=None
    if resolved is not None:
        identities=[dict(id=key,canonical_lot_id=resolved[key],**{k:lots[resolved[key]][1][k] for k in ('item_id','unit','quantity')}) for key in sorted(resolved)]
        combined={}
        for _,row in lots.values():
            key=(row['item_id'],row['unit']);combined[key]=combined.get(key,0)+row['quantity']
        totals=[dict(item_id=k[0],unit=k[1],quantity=q) for k,q in sorted(combined.items())]
    result=c.base(raw,'outlands-lot-identity-review-v1',dict(lots=lc,aliases=ac),issues)
    result.update(identities=identities,canonical_totals=totals,lot_contract_sha256=c.lot_pin(lots,aliases) if resolved is not None else None,
                  physical_identity_verified=False,stock_changed=False)
    return result

def main(argv=None):return c.cli('Resolve explicit lot aliases; no physical identity proof or stock changes.',check,argv)
if __name__=='__main__':raise SystemExit(main())
