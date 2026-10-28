"""Binary metrics, tied-score ranking and descriptive reliability bins."""
import math
from . import contracts as c,runtime as r


def calculate(labels,scores,threshold):
    if not labels or len(labels)!=len(scores) or len(labels)>1200:raise r.WorkbenchError('METRIC_LENGTH_INVALID')
    c.number(threshold,0,1)
    for label in labels:c.integer(label,0,1)
    for score in scores:c.number(score,0,1)
    positives=sum(labels);negatives=len(labels)-positives;tp=fp=tn=fn=0
    for label,score in zip(labels,scores):
        if score>=threshold:
            if label:tp+=1
            else:fp+=1
        elif label:fn+=1
        else:tn+=1
    # Average ranks give tied positive/negative pairs half credit.
    ascending=sorted(zip(scores,labels));rank_sum=0.;i=0
    while i<len(ascending):
        j=i+1
        while j<len(ascending) and ascending[j][0]==ascending[i][0]:j+=1
        rank_sum+=sum(label for _,label in ascending[i:j])*(i+1+j)/2;i=j
    auc=(rank_sum-positives*(positives+1)/2)/(positives*negatives) if positives and negatives else None
    descending=sorted(zip(scores,labels),reverse=True);seen=found=0;ap=0.;i=0
    while i<len(descending):
        j=i+1
        while j<len(descending) and descending[j][0]==descending[i][0]:j+=1
        gained=sum(label for _,label in descending[i:j]);found+=gained;seen+=j-i
        if positives:ap+=(gained/positives)*(found/seen)
        i=j
    bins=[]
    for index in range(5):
        items=[(score,label) for score,label in zip(scores,labels) if min(4,int(score*5))==index]
        bins.append(dict(lower=index/5,upper=(index+1)/5,count=len(items),mean_score=math.fsum(s for s,_ in items)/len(items) if items else None,positive_fraction=sum(y for _,y in items)/len(items) if items else None))
    clipped=[min(1-1e-15,max(1e-15,score)) for score in scores]
    return dict(rows=len(labels),positives=positives,negatives=negatives,threshold=threshold,confusion=dict(tp=tp,fp=fp,tn=tn,fn=fn),accuracy=(tp+tn)/len(labels),precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,roc_auc=auc,average_precision=ap if positives else None,brier=math.fsum((score-label)**2 for score,label in zip(scores,labels))/len(labels),log_loss=-math.fsum(label*math.log(score)+(1-label)*math.log1p(-score) for score,label in zip(clipped,labels))/len(labels),reliability_bins=bins,scores_calibrated=False)
