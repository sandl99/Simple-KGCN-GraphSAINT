import numpy as np
import os
import argparse

prefix = '../../data/'

def load_data(args):
    n_user, n_item, train_data, eval_data, test_data = load_rating(args)
    n_entity, n_relation, adj_entity, adj_relation = load_kg(args)
    print('data loaded.')

    return n_user, n_item, n_entity, n_relation, train_data, eval_data, test_data, adj_entity, adj_relation


def load_rating(args):
    print('reading rating file ...')

    # reading rating file
    rating_file = prefix + args.dataset + '/ratings_final'
    if os.path.exists(rating_file + '.npy'):
        rating_np = np.load(rating_file + '.npy')
    else:
        rating_np = np.loadtxt(rating_file + '.txt', dtype=np.int64)
        np.save(rating_file + '.npy', rating_np)

    # add += 1 for item
    rating_np[:, 1] = rating_np[:, 1] + 1
    n_user = len(set(rating_np[:, 0]))
    n_item = len(set(rating_np[:, 1]))
    train_data, eval_data, test_data = dataset_split(rating_np, args)

    return n_user, n_item, train_data, eval_data, test_data
    # return n_item, train_data


def dataset_split(rating_np, args):
    print('splitting dataset ...')

    # train:eval:test = 6:2:2
    eval_ratio = 0.2
    test_ratio = 0.2
    n_ratings = rating_np.shape[0]

    eval_indices = np.random.choice(list(range(n_ratings)), size=int(n_ratings * eval_ratio), replace=False)
    left = set(range(n_ratings)) - set(eval_indices)
    test_indices = np.random.choice(list(left), size=int(n_ratings * test_ratio), replace=False)
    train_indices = list(left - set(test_indices))
    if args.ratio < 1:
        train_indices = np.random.choice(list(train_indices), size=int(len(train_indices) * args.ratio), replace=False)

    train_data = rating_np[train_indices]
    eval_data = rating_np[eval_indices]
    test_data = rating_np[test_indices]

    return train_data, eval_data, test_data


def load_kg(args):
    print('reading KG file ...')

    # reading kg file
    kg_file = prefix + args.dataset + '/kg_final'
    if os.path.exists(kg_file + '.npy'):
        kg_np = np.load(kg_file + '.npy')
    else:
        kg_np = np.loadtxt(kg_file + '.txt', dtype=np.int64)
        np.save(kg_file + '.npy', kg_np)

    n_entity = len(set(kg_np[:, 0]) | set(kg_np[:, 2]))
    n_relation = len(set(kg_np[:, 1]))

    kg = construct_kg(kg_np)
    adj_row, adj_col, adj_relation = construct_adj(args, kg, n_entity)

    return n_entity + 1, n_relation, (adj_row, adj_col), adj_relation


def construct_kg(kg_np):
    print('constructing knowledge graph ...')
    kg = dict()
    for triple in kg_np:
        head = triple[0] + 1
        relation = triple[1] + 1
        tail = triple[2] + 1
        # treat the KG as an undirected graph
        if head not in kg:
            kg[head] = []
        kg[head].append((tail, relation))
        if tail not in kg:
            kg[tail] = []
        kg[tail].append((head, relation))
    return kg


def construct_adj(args, kg, entity_num):
    print('constructing adjacency matrix ...')
    # each line of adj_entity stores the sampled neighbor entities for a given entity
    # each line of adj_relation stores the corresponding sampled neighbor relations
    # adj_entity = np.zeros([entity_num, args.neighbor_sample_size], dtype=np.int64)
    # adj_relation = np.zeros([entity_num, args.neighbor_sample_size], dtype=np.int64)
    adj_row = []
    adj_col = []
    adj_relation = []
    length = []
    for entity in range(1, entity_num + 1):
        neighbors = kg[entity]
        n_neighbors = len(neighbors)
        # if n_neighbors >= args.neighbor_sample_size:
        #     sampled_indices = np.random.choice(list(range(n_neighbors)), size=args.neighbor_sample_size, replace=False)
        # else:
        #     sampled_indices = np.random.choice(list(range(n_neighbors)), size=args.neighbor_sample_size, replace=True)
        #
        # adj_entity[entity] = np.array([neighbors[i][0] for i in sampled_indices])
        # adj_relation[entity] = np.array([neighbors[i][1] for i in sampled_indices])
        adj_row.extend([entity] * n_neighbors)
        adj_col.extend([neighbors[i][0] for i in range(n_neighbors)])
        adj_relation.extend([neighbors[i][1] for i in range(n_neighbors)])
        length.append(n_neighbors)
    length = np.array(length)
    return np.array(adj_row), np.array(adj_col), np.array(adj_relation)
#
# if __name__ == '__main__':
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--dataset', default='movie')
#     parser.add_argument('--ratio', default=1)
#     parser.add_argument('--neighbor_sample_size', default=8)
#     args = parser.parse_args()
#     load_kg(args)
#     i = 1


def load_kg_ver0(args):
    print('reading KG file ...')

    # reading kg file
    kg_file = prefix + args.dataset + '/kg_final'
    if os.path.exists(kg_file + '.npy'):
        kg_np = np.load(kg_file + '.npy')
    else:
        kg_np = np.loadtxt(kg_file + '.txt', dtype=np.int64)
        np.save(kg_file + '.npy', kg_np)

    n_entity = len(set(kg_np[:, 0]) | set(kg_np[:, 2]))
    n_relation = len(set(kg_np[:, 1]))

    kg = construct_kg(kg_np)
    adj_entity, adj_relation = construct_adj_ver0(args, kg, n_entity + 1)

    return adj_entity, adj_relation


def construct_adj_ver0(args, kg, entity_num):
    print('constructing adjacency matrix ...')
    # each line of adj_entity stores the sampled neighbor entities for a given entity
    # each line of adj_relation stores the corresponding sampled neighbor relations
    adj_entity = np.zeros([entity_num, args.neighbor_sample_size_eval], dtype=np.int64)
    adj_relation = np.zeros([entity_num, args.neighbor_sample_size_eval], dtype=np.int64)
    for entity in range(1, entity_num):
        neighbors = kg[entity]
        n_neighbors = len(neighbors)
        if n_neighbors >= args.neighbor_sample_size_eval:
            sampled_indices = np.random.choice(list(range(n_neighbors)), size=args.neighbor_sample_size_eval, replace=False)
        else:
            sampled_indices = np.append(np.arange(n_neighbors), np.full((args.neighbor_sample_size_eval - n_neighbors), -1))
        adj_entity[entity] = np.array([neighbors[i][0] if i != -1 else 0 for i in sampled_indices])
        adj_relation[entity] = np.array([neighbors[i][1] if i != -1 else 0 for i in sampled_indices])

    return adj_entity, adj_relation
