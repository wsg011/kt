#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Author  :   wsg011
@Email   :   wsg20110828@163.com
@Time    :   2020/10/20 16:08:36
@Desc    :   
'''
import os
import logging
import argparse
import numpy as np
import pandas as pd
from tqdm import tqdm
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

import torch
import torch.nn as nn
import torch.nn.utils.rnn as rnn_utils
from torch.utils.data import DataLoader

from dataset import SAKTDataset
from model.sakt import SAKTModel

logger = logging.Logger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("--batch_size", default=64, type=int, help="data generator size")
parser.add_argument("--dataset", default="assistments", help="training dataset name")
parser.add_argument("--epochs", default=50, help="training epoch numbers")
parser.add_argument("--lr", default=0.001, help="learning rate")
parser.add_argument("--model", default="dkt", help="train model")
parser.add_argument("--max_seq", default=100, help="max question answer sequence length")
parser.add_argument("--n_skill", default=124, type=int, help="training dataset size")
parser.add_argument("--root", default="../data", help="dataset file path")
args = parser.parse_args()


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
        questions = item[1].to(device).long()
        label = item[2].to(device).float()

        optim.zero_grad()
        output, _ = model(x, questions) 
        loss = criterion(output, label)
        loss.backward()
        optim.step()
        train_loss.append(loss.item())
        
        output = output[:, -1]
        label = label[:, -1]  
        pred = (output >= 0.5).long()

        num_corrects += (pred == label).sum().item()
        num_total += len(label)

        labels.extend(label.view(-1).data.cpu().numpy())
        outs.extend(output.view(-1).data.cpu().numpy())

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
        questions = item[1].to(device).long()
        label = item[2].to(device).float()

        with torch.no_grad():
            output, _ = model(x, questions)
        loss = criterion(output, label)
        val_loss.append(loss.item())

        output = output[:, -1]
        label = label[:, -1]   
        pred = (output >= 0.5).long()
        num_corrects += (pred == label).sum().item()
        num_total += len(label)

        labels.extend(label.view(-1).data.cpu().numpy())
        outs.extend(output.view(-1).data.cpu().numpy())

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
        raise KeyError("dataset not find.")

    train_dataset = SAKTDataset(path+"/train.csv", max_seq=100, n_skill=n_skill)
    val_dataset = SAKTDataset(path+"/val.csv", max_seq=100, n_skill=n_skill)

    train_dataloader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=8)
    
    val_dataloader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=True, num_workers=8)
    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    model = SAKTModel(n_skill, embed_dim=128)
    # optimizer = torch.optim.SGD(model.parameters(), lr=1e-3, momentum=0.99, weight_decay=0.005)
    optimizer = torch.optim.Adam(model.parameters())
    criterion = nn.BCELoss()

    model.to(device)
    criterion.to(device)

    epochs = args.epochs
    for epoch in range(epochs):
        loss, acc, auc = train(model, train_dataloader, optimizer, criterion, device)
        print("epoch - {} train_loss - {:.2f} acc - {:.3f} auc - {:.4f}".format(epoch, loss, acc, auc))

        val_loss, val_acc, val_auc = validation(model, val_dataloader, criterion, device)
        print("epoch - {} vall_loss - {:.2f} acc - {:.3f} auc - {:.4f}".format(epoch, val_loss, val_acc, val_auc))



