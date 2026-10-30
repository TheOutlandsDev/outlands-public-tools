"""Bounded supplied price books, quote arithmetic and selected basket comparisons."""
from fractions import Fraction
import re
import toolkit as t
import decision_core as c

def number(value,maximum=10**18,positive=False):
    t.require(type(value) is str and re.fullmatch(r'(?:0|[1-9][0-9]{0,18})(?:\.[0-9]{1,6})?',value),'DECIMAL_INVALID')
    exact=Fraction(value);t.require(exact<=maximum and (exact>0 if positive else exact>=0),'DECIMAL_RANGE_INVALID')
    text=value.rstrip('0').rstrip('.') if '.' in value else value
    return exact,text

def currency(row):
    t.require(type(row['currency']) is str and re.fullmatch(r'[A-Z]{3}',row['currency']),'CURRENCY_INVALID')
    t.integer(row['minor_digits'],4);t.require(row['rounding'] in ('half_up','half_even','down'),'ROUNDING_INVALID')

def rounded(exact,digits,rule):
    t.require(exact>=0,'NEGATIVE_AMOUNT');scaled=exact*10**digits;whole,remainder=divmod(scaled.numerator,scaled.denominator)
    if rule!='down' and (2*remainder>scaled.denominator or (2*remainder==scaled.denominator and (rule=='half_up' or whole%2))):whole+=1
    t.require(whole<=10**18*10**digits,'AMOUNT_LIMIT');return whole

def money(units,digits):
    whole,part=divmod(units,10**digits)
    return str(whole)+('.'+str(part).zfill(digits) if digits else '')

def minor(value,digits):
    exact,_=number(value);scaled=exact*10**digits;t.require(scaled.denominator==1,'MINOR_UNIT_PRECISION_INVALID');return scaled.numerator

def nested(value,parser,maximum,minimum=1,ordered=False):
    t.require(type(value) is list and minimum<=len(value)<=maximum,'NESTED_LIMIT');seen=set();out=[]
    for row in value:
        key,normalized=parser(row);t.require(key not in seen,'NESTED_ID_DUPLICATE');seen.add(key);out.append(normalized)
    return out if ordered else sorted(out,key=lambda row:row['id'])

def item(row):
    key,out=c.record(row,{'id','unit','tiers'},('id','unit'));tiers=row['tiers'];t.require(type(tiers) is list and 1<=len(tiers)<=16,'TIER_LIMIT');out['tiers']=[];previous=None
    for tier in tiers:
        t.fields(tier,{'minimum_quantity','unit_price'});minimum,text=number(tier['minimum_quantity'],10**6);_,price=number(tier['unit_price'],10**9)
        t.require(minimum==0 if previous is None else minimum>previous,'TIER_ORDER_OR_COVERAGE_INVALID');previous=minimum
        out['tiers'].append(dict(minimum_quantity=text,unit_price=price))
    return key,out

def book(row):
    key,out=c.record(row,{'id','revision','currency','minor_digits','rounding','items'},('id',),('revision',));currency(row);out['items']=nested(row['items'],item,256);return key,out

def pricing_line(row,asserted=True):
    fields={'id','item','unit','quantity'}|({'unit_price'} if asserted else set());key,out=c.record(row,fields,('id','item','unit'));_,out['quantity']=number(row['quantity'],10**6,True)
    if asserted:_,out['unit_price']=number(row['unit_price'],10**9)
    return key,out

def quote(row):
    key,out=c.record(row,{'id','revision','price_book','price_book_revision','price_book_sha256','lines'},('id','price_book'),('revision','price_book_revision'));t.sha(row['price_book_sha256']);out['lines']=nested(row['lines'],pricing_line,256);return key,out

def basket(row):
    key,out=c.record(row,{'id','revision','lines'},('id',),('revision',));out['lines']=nested(row['lines'],lambda v:pricing_line(v,False),256);return key,out

def arithmetic_line(row):
    key,out=c.record(row,{'id','quantity','unit_price'},('id',));_,out['quantity']=number(row['quantity'],10**6,True);_,out['unit_price']=number(row['unit_price'],10**9);return key,out

def adjustment(row):
    key,out=c.record(row,{'id','kind','value'},('id',));t.require(row['kind'] in ('discount_fixed','surcharge_fixed','discount_rate','surcharge_rate'),'ADJUSTMENT_KIND_INVALID');_,out['value']=number(row['value'],1 if row['kind'].endswith('_rate') else 10**18);return key,out

def arithmetic_quote(row):
    key,out=c.record(row,{'id','revision','currency','minor_digits','rounding','lines','adjustments'},('id',),('revision',));currency(row);out['lines']=nested(row['lines'],arithmetic_line,256);out['adjustments']=nested(row['adjustments'],adjustment,32,0,True)
    for a in out['adjustments']:
        if a['kind'].endswith('_fixed'):minor(a['value'],out['minor_digits'])
    return key,out

def amount_row(row,reference):
    t.fields(row,{reference,'amount'});t.identifier(row[reference]);_,text=number(row['amount']);return row[reference],{reference:row[reference],'amount':text}

def amounts(rows,reference):
    t.require(type(rows) is list and len(rows)<=256,'AMOUNT_ROWS_LIMIT');seen=set();out=[]
    for row in rows:
        key,normalized=amount_row(row,reference);t.require(key not in seen,'AMOUNT_ID_DUPLICATE');seen.add(key);out.append(normalized)
    return sorted(out,key=lambda row:row[reference])

def claim(row):
    key,out=c.record(row,{'id','revision','quote','quote_revision','quote_sha256','line_totals','adjustment_totals','subtotal','total'},('id','quote'),('revision','quote_revision'));t.sha(row['quote_sha256']);out['line_totals']=amounts(row['line_totals'],'line');out['adjustment_totals']=amounts(row['adjustment_totals'],'adjustment')
    for name in ('subtotal','total'):_,out[name]=number(row[name])
    return key,out

def collect(value,parser,side,counts,issues):
    t.require(type(value) is list and len(value)<=128,'COHORT_LIMIT');rows,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if not rows:c.issue(issues,side,0,'COHORT_EMPTY')
    return rows

def reference(row,name,targets,side,position,issues):
    target=targets.get(row[name])
    if target is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    selected=target[1]
    if row[name+'_revision']!=selected['revision'] or row[name+'_sha256']!=c.pin(selected):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return selected

def price_lines(lines,selected):
    items={v['id']:v for v in selected['items']};out=[]
    for line in lines:
        entry=items.get(line['item']);result=dict(id=line['id'],state='valid',selected_minimum_quantity=None,expected_unit_price=None,rounded_extension=None)
        if entry is None:result['state']='item_unknown'
        elif line['unit']!=entry['unit']:result['state']='unit_mismatch'
        else:
            quantity=Fraction(line['quantity']);tier=next(v for v in reversed(entry['tiers']) if Fraction(v['minimum_quantity'])<=quantity);price=Fraction(tier['unit_price'])
            result.update(selected_minimum_quantity=tier['minimum_quantity'],expected_unit_price=tier['unit_price'],rounded_extension=money(rounded(quantity*price,selected['minor_digits'],selected['rounding']),selected['minor_digits']))
            if 'unit_price' in line and Fraction(line['unit_price'])!=price:result['state']='price_mismatch'
        out.append(result)
    return out

def calculate(row):
    digits=row['minor_digits'];rule=row['rounding'];lines=[];subtotal=0
    for line in row['lines']:
        units=rounded(Fraction(line['quantity'])*Fraction(line['unit_price']),digits,rule);subtotal+=units;lines.append(dict(line=line['id'],amount=money(units,digits)))
    t.require(subtotal<=10**18*10**digits,'AMOUNT_LIMIT');running=subtotal;adjustments=[]
    for a in row['adjustments']:
        magnitude=rounded(Fraction(running,10**digits)*Fraction(a['value']),digits,rule) if a['kind'].endswith('_rate') else minor(a['value'],digits)
        if a['kind'].startswith('discount'):t.require(magnitude<=running,'DISCOUNT_EXCEEDS_RUNNING_TOTAL');running-=magnitude
        else:running+=magnitude
        t.require(running<=10**18*10**digits,'AMOUNT_LIMIT');adjustments.append(dict(adjustment=a['id'],amount=money(magnitude,digits)))
    return dict(line_totals=lines,adjustment_totals=adjustments,subtotal=money(subtotal,digits),total=money(running,digits))

def compare_amounts(supplied,expected,key,digits):
    actual={v[key]:minor(v['amount'],digits) for v in supplied};wanted={v[key]:minor(v['amount'],digits) for v in expected}
    return dict(missing_count=len(wanted.keys()-actual.keys()),unknown_count=len(actual.keys()-wanted.keys()),mismatch_ids=sorted(k for k in wanted.keys()&actual.keys() if wanted[k]!=actual[k]))

def output(raw,mode,counts,issues,assessment,pins):
    out=c.base(raw,'outlands-quote-pricing-'+mode+'-report-v1',counts,issues);qualified=assessment is not None
    out.update(assessment=assessment,qualified_scope_sha256=c.pin(pins) if qualified and not issues else None,cohort_sha256=pins if qualified else None,network_requests_performed=False,records_changed=False,currency_conversion_performed=False,tax_rules_verified=False,approval_verified=False,whole_catalog_compatibility_verified=False)
    return out

def check(raw,mode):
    value=t.decode(raw);fields={'books':{'price_books'},'lines':{'price_books','quotes'},'totals':{'quotes','claims'},'scenarios':{'baseline_price_books','candidate_price_books','baskets'}}[mode]
    t.fields(value,fields|{'format'});t.require(value['format']=='outlands-quote-pricing-'+mode+'-v1','FORMAT_INVALID');counts={};issues=[];pins={};assessment=None
    parsers={'price_books':book,'quotes':arithmetic_quote if mode=='totals' else quote,'claims':claim,'baseline_price_books':book,'candidate_price_books':book,'baskets':basket};scope={}
    for key in sorted(fields):scope[key]=collect(value[key],parsers[key],key,counts,issues);pins[key]=c.cohort_pin(scope[key])
    if mode=='scenarios':
        for key in ('baseline_price_books','candidate_price_books'):
            if len(scope[key])!=1:c.issue(issues,key,0,'EXACTLY_ONE_BOOK_REQUIRED')
        if not issues:
            left=next(iter(scope['baseline_price_books'].values()))[1];right=next(iter(scope['candidate_price_books'].values()))[1]
            if (left['id'],left['revision'])==(right['id'],right['revision']) and c.pin(left)!=c.pin(right):c.issue(issues,'candidate_price_books',0,'SAME_REVISION_DEFINITION_CONFLICT')
            if any(left[k]!=right[k] for k in ('currency','minor_digits')):c.issue(issues,'candidate_price_books',0,'CURRENCY_OR_MINOR_UNITS_INCOMPARABLE')
    elif mode in ('lines','totals'):
        name='price_book' if mode=='lines' else 'quote';source='quotes' if mode=='lines' else 'claims';targets='price_books' if mode=='lines' else 'quotes'
        for _,(position,row) in sorted(scope[source].items()):reference(row,name,scope[targets],source,position,issues)
        if mode=='totals':
            for key,(position,row) in sorted(scope['quotes'].items()):
                try:calculate(row)
                except t.Rejected as error:c.issue(issues,'quotes',position,str(error))
            for _,(position,row) in sorted(scope['claims'].items()):
                target=scope['quotes'].get(row['quote'])
                if target:
                    try:
                        digits=target[1]['minor_digits']
                        for v in row['line_totals']+row['adjustment_totals']:minor(v['amount'],digits)
                        minor(row['subtotal'],digits);minor(row['total'],digits)
                    except t.Rejected as error:c.issue(issues,'claims',position,str(error))
    if not issues:
        if mode=='books':assessment=dict(price_books=[dict(id=k,revision=v['revision'],sha256=c.pin(v),item_count=len(v['items'])) for k,(_,v) in sorted(scope['price_books'].items())])
        elif mode=='lines':
            results=[]
            for key,(position,row) in sorted(scope['quotes'].items()):
                selected=scope['price_books'][row['price_book']][1];lines=price_lines(row['lines'],selected);valid=all(v['state']=='valid' for v in lines);results.append(dict(id=key,valid=valid,lines=lines))
                if not valid:c.issue(issues,'quotes',position,'LINE_PRICING_MISMATCH')
            assessment=dict(quotes=results)
        elif mode=='totals':
            results=[]
            for key,(position,row) in sorted(scope['claims'].items()):
                target=scope['quotes'][row['quote']][1];expected=calculate(target);digits=target['minor_digits'];line=compare_amounts(row['line_totals'],expected['line_totals'],'line',digits);adj=compare_amounts(row['adjustment_totals'],expected['adjustment_totals'],'adjustment',digits);subtotal=minor(row['subtotal'],digits)==minor(expected['subtotal'],digits);total=minor(row['total'],digits)==minor(expected['total'],digits)
                valid=not any(line.values()) and not any(adj.values()) and subtotal and total;results.append(dict(id=key,valid=valid,expected=expected,line_coverage=line,adjustment_coverage=adj,subtotal_matches=subtotal,total_matches=total))
                if not valid:c.issue(issues,'claims',position,'TOTAL_CLAIM_MISMATCH')
            assessment=dict(claims=results)
        else:
            results=[]
            for key,(position,row) in sorted(scope['baskets'].items()):
                before=price_lines(row['lines'],left);after=price_lines(row['lines'],right);comparable=all(v['state']=='valid' for v in before+after);same=comparable and before==after
                results.append(dict(id=key,comparable=comparable,equal=same,baseline=before,candidate=after))
                if not comparable:c.issue(issues,'baskets',position,'BASKET_INCOMPARABLE')
                elif not same:c.issue(issues,'baskets',position,'PRICING_OUTCOME_CHANGED')
            assessment=dict(baskets=results)
    return output(raw,mode,counts,issues,assessment,pins)
