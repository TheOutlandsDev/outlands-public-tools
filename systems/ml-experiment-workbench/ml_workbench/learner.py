"""Train-only observed-mean imputation/scaling and full-batch L2 logistic baseline."""
import math
from . import runtime as r


def sigmoid(value):
    if value>=0:return 1/(1+math.exp(-value))
    exp=math.exp(value);return exp/(1+exp)


def preprocessing(rows,names):
    means=[];scales=[];missing=[];constant=[]
    for name in names:
        values=[row['features'][name] for row in rows if row['features'][name] is not None]
        if not values:raise r.WorkbenchError('NO_TRAINING_FEATURE_VALUES')
        mean=math.fsum(values)/len(values);scale=math.sqrt(math.fsum((x-mean)**2 for x in values)/len(values));is_constant=scale<1e-12
        means.append(mean);scales.append(1. if is_constant else scale);missing.append(len(rows)-len(values));constant.append(is_constant)
    return dict(feature_names=names,means=means,scales=scales,training_missing_counts=missing,constant_or_tiny_scale=constant,variance_population='observed_training_values_only')


def transform(rows,preprocessor):
    names=preprocessor['feature_names'];means=preprocessor['means'];scales=preprocessor['scales'];result=[]
    for row in rows:
        values=[((row['features'][name] if row['features'][name] is not None else mean)-mean)/scale for name,mean,scale in zip(names,means,scales)]
        if any(not math.isfinite(x) for x in values):raise r.WorkbenchError('TRANSFORM_NONFINITE')
        result.append(values)
    return result


def scores(model,rows):
    transformed=transform(rows,model['preprocessing']);weights=model['weights'];bias=model['intercept']
    return [sigmoid(bias+math.fsum(w*x for w,x in zip(weights,values))) for values in transformed]


def fit(rows,names,config):
    preprocessor=preprocessing(rows,names);matrix=transform(rows,preprocessor);labels=[row['outcome'] for row in rows];weights=[0.]*len(names);bias=0.;n=len(rows)
    for _ in range(config['iterations']):
        residual=[sigmoid(bias+math.fsum(w*x for w,x in zip(weights,row)))-label for row,label in zip(matrix,labels)]
        gradients=[math.fsum(error*row[j] for error,row in zip(residual,matrix))/n+config['l2']*weights[j] for j in range(len(weights))]
        weights=[w-config['learning_rate']*gradient for w,gradient in zip(weights,gradients)];bias-=config['learning_rate']*math.fsum(residual)/n
    if any(not math.isfinite(x) for x in weights+[bias]):raise r.WorkbenchError('MODEL_NONFINITE')
    return dict(format='outlands-logistic-baseline-v1',algorithm='full_batch_binary_cross_entropy_plus_half_l2_weight_norm',preprocessing=preprocessor,weights=weights,intercept=bias,learner=config,training_rows=n,training_prevalence=sum(labels)/n,scores_calibrated=False,executable_serialization=False)
