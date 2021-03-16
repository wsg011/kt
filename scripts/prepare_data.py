#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Author  :   wsg011
@Email   :   wsg20110828@163.com
@Time    :   2020/10/20 15:27:46
@Desc    :   
'''
import os
import csv
import argparse
import pandas as pd
from sklearn.model_selection import train_test_split


parser = argparse.ArgumentParser()
parser.add_argument("--root", default="../data")
parser.add_argument("--dataset", default="ASSISTments2009", type=str)
parser.add_argument("--input", default="skill_builder_data_corrected.csv", type=str)
args = parser.parse_args()


def save_file(data, file_name):
    csv_file = open(file_name, "w")
    # csv_file.write("user_id,skill_id,correct\n")

    for user_id in data.index:
        sample = data[user_id]

        q = sample[0]
        qa = sample[1]

        if len(q) < 2:
            continue
        
        user_id = str(int(user_id))
        q = [str(int(x)) for x in q]
        qa = [str(int(x)) for x in qa]
        csv_file.write(user_id+"\n")
        csv_file.write(",".join(q)+"\n")
        csv_file.write(",".join(qa)+"\n")
    
    csv_file.close()

    return True

if __name__ == "__main__":
    path = os.path.join(args.root, args.dataset, args.input)

    if args.dataset in ["assistments2009", "assistments2012", "assistments2015"]:
        df = pd.read_csv(path)
        
        data = pd.DataFrame()
        data["user_id"] = df["user_id"]
        data["skill_id"] = df["skill_id"]
        data["correct"] = df["correct"]
        data = data.dropna()

    elif args.dataset == "riid":
        dtype = {'timestamp': 'int64', 'user_id': 'int32' ,
             'content_id': 'int16','content_type_id': 'int8',
             'answered_correctly':'int8'}

        train_df = pd.read_csv(path, usecols=[1, 2, 3,4,7], dtype=dtype)
        train_df = train_df[train_df.content_type_id == False]
        train_df = train_df.sort_values(['timestamp'], ascending=True).reset_index(drop = True)

        data = pd.DataFrame()
        data["user_id"] = train_df["user_id"]
        data["skill_id"] = train_df["content_id"]
        data["correct"] = train_df["answered_correctly"]
    
    elif args.dataset == "xkl":
        df = pd.read_csv(path)

        data = df

    else:
        raise KeyError("can't get dataset name")

    user_ids = data["user_id"].unique()

    skill_ids = data["skill_id"].unique()
    skill_ids = [int(x) for x in skill_ids]
    skill_ids = sorted(skill_ids)

    group = data.groupby('user_id').apply(lambda r: (
            r['skill_id'].values,
            r['correct'].values))
    
    train, val = train_test_split(group, test_size=0.3)

    # save skill_id
    skill_df = pd.DataFrame(skill_ids, columns=["skill_id"])
    skill_df.to_csv(os.path.join(args.root, args.dataset, "skills.csv"), index=False)

    # save user_id
    user_ids = [int(x) for x in user_ids]
    user_df = pd.DataFrame(user_ids, columns=["user_id"])
    user_df.to_csv(os.path.join(args.root, args.dataset, "users.csv"), index=False)

    # save train and val
    train_fn = os.path.join(args.root, args.dataset, "train.csv")
    save_file(train, train_fn)

    val_fn = os.path.join(args.root, args.dataset, "val.csv")
    save_file(val, val_fn)