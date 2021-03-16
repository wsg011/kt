#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Author  :   wsg011
@Email   :   wsg20110828@163.com
@Time    :   2020/10/20 16:08:36
@Desc    :   
'''
import os
import sys
import logging
import argparse
import itertools
import numpy as np
import pandas as pd
from tqdm import tqdm
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

import torch
import torch.nn as nn
import torch.nn.utils.rnn as rnn_utils
from torch.utils.data import DataLoader, Dataset

sys.path.append("../")
from torchkt.model import DKTModel

logger = logging.Logger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("--batch_size", default=1024, help="data generator size")
parser.add_argument("--dataset", default="assistments", help="training dataset name")
parser.add_argument("--epochs", default=50, help="training epoch numbers")
parser.add_argument("--lr", default=0.001, help="learning rate")
parser.add_argument("--model", default="dkt", help="train model")
parser.add_argument("--max_seq", default=100, help="max question answer sequence length")
parser.add_argument("--root", default="../data", help="dataset file path")
args = parser.parse_args()


class DKTDataset(Dataset):
    def __init__(self, fn, n_skill, max_seq=100):
        super(DKTDataset, self).__init__()
        self.n_skill = n_skill
        self.max_seq = max_seq

        self.user_ids = []
        self.samples = []
        with open(fn, "r") as csv_f:
            for student_id, q, qa in itertools.zip_longest(*[csv_f] * 3):
                student_id = int(student_id.strip())
                q = [int(x) for x in q.strip().split(",") if x]
                qa = [int(x) for x in qa.strip().split(",") if x]

                assert len(q) == len(qa)
                if len(q) <= 2:
                    continue

                self.user_ids.append(student_id)
                self.samples.append((q, qa))

    def __len__(self):
        return len(self.user_ids)

    def __getitem__(self, index):
        user_id = self.user_ids[index]
        q_, qa_ = self.samples[index]
        seq_len = len(q_)

        q = np.zeros(self.max_seq, dtype=int)
        qa = np.zeros(self.max_seq, dtype=int)
        if seq_len >= self.max_seq:
            q[:] = q_[-self.max_seq:]
            qa[:] = qa_[-self.max_seq:]
        else:
            q[-seq_len:] = q_
            qa[-seq_len:] = qa_

        target_id = q[-1]
        label = qa[-1]

        q = q[:-1].astype(np.int)
        qa = qa[:-1].astype(np.int)
        x = q[:-1]
        x += (qa[:-1] == 1) * self.n_skill

        target_id = np.array([target_id]).astype(np.int)
        label = np.array([label]).astype(np.int)

        return x, target_id, label 


def train(model, train_iterator, optim, criterion, device="cpu"):
    model.train()

    train_loss = []
    num_corrects = 0
    num_total = 0
    labels = []
    outs = []

    tbar = tqdm(train_iterator)
    for item in tbar:
        x = item[0].to(device).long()
        target_id = item[1].to(device).long()
        label = item[2].to(device).float()

        optim.zero_grad()
        output = model(x)

        output = torch.gather(output, -1, target_id)
        pred = (torch.sigmoid(output) >= 0.5).long()
        
        loss = criterion(output, label)
        loss.backward()
        optim.step()

        train_loss.append(loss.item())
        num_corrects += (pred == label).sum().item()
        num_total += len(label)

        labels.extend(label.squeeze(-1).data.cpu().numpy())
        outs.extend(output.squeeze(-1).data.cpu().numpy())

        tbar.set_description('loss - {:.4f}'.format(loss))


    acc = num_corrects / num_total
    auc = roc_auc_score(labels, outs)
    loss = np.mean(train_loss)

    return loss, acc, auc


def validation(model, val_iterator, criterion, device):
    model.eval()

    val_loss = []
    num_corrects = 0
    num_total = 0
    labels = []
    outs = []

    tbar = tqdm(val_iterator)
    for item in tbar:
        x = item[0].to(device).long()
        target_id = item[1].to(device).long()
        label = item[2].to(device).float()

        with torch.no_grad():
            output = model(x)
    
        output = torch.gather(output, -1, target_id)

        pred = (torch.sigmoid(output) >= 0.5).long()
        loss = criterion(output, label)

        val_loss.append(loss.item())
        num_corrects += (pred == label).sum().item()
        num_total += len(label)

        labels.extend(label.squeeze(-1).data.cpu().numpy())
        outs.extend(output.squeeze(-1).data.cpu().numpy())

        tbar.set_description('loss - {:.4f}'.format(loss))

    acc = num_corrects / num_total
    auc = roc_auc_score(labels, outs)
    loss = np.mean(val_loss)

    return loss, acc, auc


if __name__ == "__main__":
    path = os.path.join(args.root, args.dataset)

    if args.dataset == "riid":
        n_skill = 13523
    elif args.dataset == "assistments":
        n_skill = 124
    else:
        raise KeyError("dataset error")

    train_dataset = DKTDataset(path+"/train.csv", max_seq=100, n_skill=n_skill)
    val_dataset = DKTDataset(path+"/val.csv", max_seq=100, n_skill=n_skill)

    train_dataloader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=8)
    
    val_dataloader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=True, num_workers=8)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = DKTModel(n_skill)
    # optimizer = torch.optim.SGD(model.parameters(), lr=1e-3, momentum=0.99, weight_decay=0.005)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.BCEWithLogitsLoss()

    model.to(device)
    criterion.to(device)

    epochs = args.epochs
    for epoch in range(epochs):
        loss, acc, auc = train(model, train_dataloader, optimizer, criterion, device)
        print("epoch - {} train_loss - {:.2f} acc - {:.3f} auc - {:.3f}".format(epoch, loss, acc, auc))

        val_loss, val_acc, val_auc = validation(model, val_dataloader, criterion, device)
        print("epoch - {} vall_loss - {:.2f} acc - {:.3f} auc - {:.3f}".format(epoch, val_loss, val_acc, val_auc))



