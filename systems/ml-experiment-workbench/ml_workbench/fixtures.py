"""Invented ordinal days, grouped records and dimensionless features; no source data."""
from .learner import sigmoid


def dataset():
    state=17;rows=[]
    def uniform():
        nonlocal state
        state=(1664525*state+1013904223)%(2**32);return state/(2**32)
    for day in range(240):
        signal=round(uniform(),6);load=round(uniform(),6);ready=int(uniform()>.5);outcome=int(uniform()<sigmoid(-3+4*signal+2*load+ready));features=dict(signal=signal,load=None if day%17==0 else load,ready=ready)
        delayed=day in (118,119,178,179,238,239)
        rows.append(dict(row_id='sample-row-'+str(day),group_id='sample-group-'+str(day//2),decision_day=day,label_available_day=day+(25 if delayed else 3),features=features,feature_available_day={name:day if value is not None else None for name,value in features.items()},outcome=outcome))
    return dict(format='outlands-ml-dataset-v1',dataset_id='sample-ml',title='Fictional chronological binary outcomes',feature_names=['signal','load','ready'],rows=rows)
