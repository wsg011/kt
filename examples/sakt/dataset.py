import itertools
import numpy as np
import pandas as pd

import torch
from torch.utils.data import Dataset


class SAKTDataset(Dataset):
    def __init__(self, fn, n_skill, max_seq=100):
        super(SAKTDataset, self).__init__()
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
        """
        get sakt model input
        args:
            index
        returns:
            x:
            question_id:
            target_id:
            correct
        """
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

        # target_id = np.array([q[-1]])
        # label = np.array([qa[-1]])
        questions = q[1:].copy()
        correctness = qa[1:]
    
        x = q[:-1].copy()
        x += (qa[:-1] == 1) * self.n_skill

        return x, questions, correctness
        
if __name__ == "__main__":
    dataset = SAKTDataset("../data/ASSISTments2009/train.csv", n_skill=124)

    x, q, target_id, label = dataset.__getitem__(10)
    print(x)
    print(q)
    print(target_id)
    print(label)