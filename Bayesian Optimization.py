# -*- coding: utf-8 -*-
"""STAT 546 Project.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1jeZXBrryC0D5XEjkhPNmwrKjLuRt14Qq

#  IMDB Movie Review Sentiment Classification

---
## Overview

A tiny LLM is fine-tuned on a portion of IMDB data using using Bayesian Optimization to predict the sentiment of a given movie review.

---
## Notes
- LLM Model Used: TinyBERT
- Source of model: HuggingFace

---
## References
1. https://huggingface.co/docs/transformers/en/training
2. https://discuss.huggingface.co/t/how-to-get-the-loss-history-when-use-trainer-train/17486/5
3. https://datascience.stackexchange.com/questions/64583/what-are-the-good-parameter-ranges-for-bert-hyperparameters-while-finetuning-it
4. https://huggingface.co/blog/ray-tune
5. https://huggingface.co/docs/transformers/en/hpo_train

---

# Initialization

## GDrive Connection
"""

from google.colab import drive
drive.mount('/content/drive')

"""## Package Installation"""

!pip install transformers datasets
!pip install accelerate -U
!pip install evaluate
!pip install bayesian-optimization
!pip install "ray[tune]"

"""## Loading Libraries, Variables and Packages"""

from datasets import load_dataset
from transformers import AutoTokenizer
from transformers import AutoModelForSequenceClassification
from transformers import TrainingArguments
import numpy as np
import evaluate
from transformers import Trainer
import pandas as pd
from datasets import concatenate_datasets
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from transformers import TextClassificationPipeline
from transformers import AutoConfig
from ray.tune.search.bayesopt import BayesOptSearch
from ray.tune.schedulers import ASHAScheduler
from ray import tune

loc= '/content/drive/MyDrive/STAT_546/'

"""# Data Loading and Transformation"""

dataset = load_dataset("imdb")
dataset["train"][100]

tokenizer = AutoTokenizer.from_pretrained("google/bert_uncased_L-2_H-128_A-2")

model = AutoModelForSequenceClassification.from_pretrained("google/bert_uncased_L-2_H-128_A-2", num_labels=2)

model.config.max_position_embeddings

def tokenize_function(examples):
    return tokenizer(examples["text"], truncation=True, max_length=512, padding='max_length')

tokenized_datasets = dataset.map(tokenize_function, batched=True)

tokenized_datasets

np.mean(tokenized_datasets['train']['label'])

tokenized_datasets

# Training on only 1/10 th of the dataset
small_train_dataset_0 = tokenized_datasets["train"].filter(lambda example: example['label'] == 0).shuffle(seed=42).select(range(1250))
small_train_dataset_1 = tokenized_datasets["train"].filter(lambda example: example['label'] == 1).shuffle(seed=42).select(range(1250))

small_train_dataset = concatenate_datasets([small_train_dataset_0, small_train_dataset_1])
small_train_dataset= small_train_dataset.shuffle(seed= 42)

small_eval_dataset_0 = tokenized_datasets["test"].filter(lambda example: example['label'] == 0).shuffle(seed=42).select(range(1250))
small_eval_dataset_1 = tokenized_datasets["test"].filter(lambda example: example['label'] == 1).shuffle(seed=42).select(range(1250))

small_eval_dataset = concatenate_datasets([small_eval_dataset_0, small_eval_dataset_1])
small_eval_dataset= small_eval_dataset.shuffle(seed= 42)

"""# Model Initialization and Training"""

metric = evaluate.load("accuracy")

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return metric.compute(predictions=predictions, references=labels)

training_args = TrainingArguments(output_dir= loc + "test_trainer", evaluation_strategy="epoch", num_train_epochs=5)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=small_train_dataset,
    eval_dataset=small_eval_dataset,
    compute_metrics=compute_metrics
)

trainer.train()

trainer.evaluate()

"""# Model Save"""

if True==False:
  pd.to_pickle(model, loc + 'non_bo_model.pickle')

if True==False:
  pd.to_pickle(pd.DataFrame(trainer.state.log_history), loc + 'non_bo_train_log.pickle')

"""# Model Usage"""

label2id = {"negative": 0, "positive": 1}
id2label = {0: "negative", 1: "positive"}

if True==False:
  model.save_pretrained(loc + 'nonbo_model')

if True==False:
  tokenizer.save_pretrained(loc + 'nonbo_model')

model_name = loc + "nonbo_model"
tokenizer_name= loc + "nonbo_model"
model_load = AutoModelForSequenceClassification.from_pretrained(model_name)
tokenizer_load = AutoTokenizer.from_pretrained(model_name)

model_load.config.label2id = label2id
model_load.config.id2label = id2label

pipe = TextClassificationPipeline(model=model_load, tokenizer=tokenizer_load, top_k=None)

pipe("I loved the movie!")

"""# Bayesian Optimization"""

tokenizer = AutoTokenizer.from_pretrained("google/bert_uncased_L-2_H-128_A-2")

metric = evaluate.load("accuracy")

def model_init():
    return AutoModelForSequenceClassification.from_pretrained("google/bert_uncased_L-2_H-128_A-2", num_labels=2)

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return metric.compute(predictions=predictions, references=labels)

training_args = TrainingArguments(output_dir= loc + "bo_test_trainer", evaluation_strategy="steps", eval_steps=320)

trainer = Trainer(
    args=training_args,
    tokenizer=tokenizer,
    train_dataset=small_train_dataset,
    eval_dataset=small_eval_dataset,
    model_init=model_init,
    compute_metrics=compute_metrics,
)

def ray_hp_space(trial):
    return {
        "learning_rate": tune.loguniform(1e-5, 5e-4),
        "weight_decay": tune.uniform(0.0, 0.1)
    }

best_trials= trainer.hyperparameter_search(
      direction="maximize",
      backend="ray",
      n_trials=5,
      search_alg=BayesOptSearch(metric="objective", mode="max"),
      scheduler=ASHAScheduler(metric="objective", mode="max"),
      hp_space= ray_hp_space
      )

# Graphs to compare training plot history

if True==True:
  pd.to_pickle(best_trials, loc + 'bo_best_trials.pickle')

"""**HyperOptSearch**"""

from ray.tune.search.hyperopt import HyperOptSearch

# Define the hyperparameter space
def hos_hp_space(trial):
    return {
        "learning_rate": tune.loguniform(1e-5, 5e-4),
        "weight_decay": tune.uniform(0.0, 0.1)
    }

# Initialize HyperOptSearch
hyperopt_search = HyperOptSearch(metric="objective", mode="max")

# Perform hyperparameter search
best_trials = trainer.hyperparameter_search(
    direction="maximize",
    backend="ray",
    n_trials=5,
    search_alg=hyperopt_search,
    scheduler=ASHAScheduler(metric="objective", mode="max"),
    hp_space=hos_hp_space
)

"""---

---
"""