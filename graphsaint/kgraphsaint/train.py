import argparse
from graphsaint.kgraphsaint import loader, utils
import logging
from graphsaint.kgraphsaint.batchsample import Minibatch
import torch
from graphsaint.kgraphsaint.models import KGraphSAINT
from graphsaint.kgraphsaint.dataloader import SubgraphRating
from torch.utils.data import DataLoader
import time
from barbar import Bar
import numpy as np

logging.basicConfig(level=logging.DEBUG)


class Args():
    def __init__(self):
        self.dataset = 'movie'
        self.aggregator = 'sum'
        self.n_epochs = 500
        self.neighbor_sample_size = 8
        self.dim = 16
        self.n_iter = 2
        self.batch_size = 65536
        self.l2_weight = 1e-7
        self.lr = 1e-3
        self.ratio = 0.8
        self.save_dir = './kgraph_models'


def parse_arg():
    # parser = argparse.ArgumentParser()
    #
    # parser.add_argument('--dataset', type=str, default='movie', help='which dataset to use')
    # parser.add_argument('--aggregator', type=str, default='sum', help='which aggregator to use')
    # parser.add_argument('--n_epochs', type=int, default=500, help='the number of epochs')
    # parser.add_argument('--neighbor_sample_size', type=int, default=8, help='the number of neighbors to be sampled')
    # parser.add_argument('--dim', type=int, default=16, help='dimension of user and entity embeddings')
    # parser.add_argument('--n_iter', type=int, default=2,
    #                     help='number of iterations when computing entity representation')
    # parser.add_argument('--batch_size', type=int, default=256, help='batch size')
    # parser.add_argument('--l2_weight', type=float, default=1e-4, help='weight of l2 regularization')
    # parser.add_argument('--lr', type=float, default=1e-3, help='learning rate')
    # parser.add_argument('--ratio', type=float, default=0.8, help='size of training dataset')
    #
    # parser.add_argument('--save_dir', type=str, default='./kgraph_models', help='directory saving KGCN')
    # return parser.parse_args()
    return Args()

def train(_model, _criterion, _optimizer, _minibatch, _train_data, _device, _args):
    logging.info(f'Starting training phase... Estimator Epoch: {_minibatch.num_training_batches()}')
    epoch = 0
    while not _minibatch.end():
        logging.info(f'-------- Epoch: {epoch} --------')
        epoch += 1
        _t0 = time.time()
        node, adj, rel = _minibatch.one_batch('train')
        node_tensor = torch.from_numpy(np.array(node)).to('cpu')
        adj = torch.from_numpy(adj).to('cpu')
        rel = torch.from_numpy(rel).to('cpu')
        reserve_node = {j: i for i, j in enumerate(node)}

        _t1 = time.time()
        logging.info(f'Sampling sub graph in {_t1-_t0: .3f} seconds')

        subgraph_rating = SubgraphRating(node, _train_data)
        data_loader = DataLoader(subgraph_rating, batch_size=_args.batch_size, drop_last=False, shuffle=True)
        _t2 = time.time()
        logging.info(f'Building DataLoader in {_t2-_t1: .3f} seconds')

        train_loss, eval_loss = 0, 0
        train_auc, eval_auc = [], []
        train_pred, train_true = np.zeros(0), np.zeros(0)
        for data in Bar(data_loader):
            users, items, labels = data['user'].to(_device), data['item'].to(_device), data['label'].type(torch.float32).to(_device)
            _optimizer.zero_grad()
            outputs = _model(users, items, reserve_node, node_tensor, adj, rel)
            loss = _criterion(outputs, labels)
            loss.backward()

            _optimizer.step()
            train_loss += loss.item()

            # detach outputs and labels
            train_pred = np.concatenate((train_pred, outputs.detach().cpu().numpy()))
            train_true = np.concatenate((train_true, labels. detach().cpu().numpy()))
        logging.info(f'Train loss: {train_loss / len(data_loader)}')
        score = utils.auc_score(train_pred, train_true, 'micro')
        logging.info(f'Train AUC : {score} micro')
        # score = utils.auc_score(train_pred, train_true, 'macro')
        # logging.info(f'Train AUC : {score} macro')

        # if epoch == 2:
        #     exit(0)


def evaluate():
    pass


def main():
    args = parse_arg()
    # Loading data
    t0 = time.time()
    logging.info('Loading knowledge graph from data')
    n_entity, n_relation, adj_entity, adj_relation = loader.load_kg(args)
    logging.info('Loading ratings data')
    n_user, n_item, train_data, eval_data, test_data = loader.load_rating(args)
    train_data = utils.reformat_train_ratings(train_data)
    utils.check_items_train(train_data, n_item)
    t1 = time.time()
    logging.info(f'Done loading data in {t1-t0 :.3f}')

    # Build GraphSAINT sampler
    mini_batch = Minibatch(adj_entity, adj_relation, n_entity, n_relation)
    utils.build_sample(mini_batch)

    # model and optimizer
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = KGraphSAINT(n_user, n_entity, n_relation, args).to(device)
    criterion = torch.nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.l2_weight)
    logging.info(f'Device: {device}')
    logging.info("Total number of parameters = {}".format(sum(p.numel() for p in model.parameters())))

    # train phases
    train(model, criterion, optimizer, mini_batch, train_data, device, args)


if __name__ == '__main__':
    main()
