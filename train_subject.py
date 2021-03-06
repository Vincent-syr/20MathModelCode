import sys
import pickle
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import numpy as np
import copy
import os
from os.path import join
from model2 import ConvNet

# super parameters
subject_num = int(sys.argv[1])
is_train = int(sys.argv[2])  # 1 train; 2 test
is_with_ave = sys.argv[3]  # w; o
test_size = 12
data_path = "./data"
batch_size = 48
epoch = 1000
learning_rate = 1e-3
weight_decay = 1e-2
loss_weight = 4.5
channel_begin = 0
channel_end = 20
print_frep = 50

# divide data into minibatches
def minibatch(data, batch_size):
    start = 0
    while True:
        end = start + batch_size
        yield data[start:end]

        start = end
        if start >= len(data):
            break

# calculate acc
def cal_acc(pred, target):
    assert len(pred) == len(target)
    acc = np.sum(pred == target) / len(pred)
    return acc

def cal_f(pred, target):
    assert len(pred) == len(target)
    tp = 0
    for i in range(len(pred)):
        if pred[i] == target[i] and pred[i] == 1:
            tp += 1
    percision = tp / np.sum(pred == 1)
    recall = tp / np.sum(target == 1)
    f_score = (2 * percision * recall) / (percision + recall)
    return f_score, percision, recall

# train function
def train_batch(model, criterion, optimizer, batch, curr_epoch, fold):

    model.zero_grad()

    # forward pass
    x = torch.FloatTensor([i for i in batch[:, 0]]).cuda()
    x = x[:, :, channel_begin: channel_end]

    _, height, width = x.size()
    x = x.view(min(batch_size, len(x)), 1, height, width)
    y = torch.FloatTensor([i for i in batch[:, 1]]).cuda()

    pred = model(x)

    # back proporgation
    loss = criterion(pred.view(-1), y)
    loss.backward()
    optimizer.step()

    pred = pred.cpu().detach().numpy().reshape(-1)
    pred = np.array([1 if n >= 0.5 else 0 for n in pred])
    return pred, loss

def weighted_BCE(predictions, labels):
    predictions = predictions.clamp(1e-6, 1 - 1e-6)
    labels = labels.clamp(0, 1)
    # loss = -labels * torch.log(predictions) - 5 * (1 - labels) * torch.log(1 - predictions)
    loss = - loss_weight * labels * torch.log(predictions) - (1 - labels) * torch.log(1 - predictions)

    return loss.mean()


def val_batch(model, criterion, optimizer, batch):
    with torch.no_grad():
        # forward pass
        x = torch.FloatTensor([i for i in batch[:, 0]]).cuda()
        x = x[:, :, channel_begin: channel_end]
        _, height, width = x.size()
        x = x.view(min(batch_size, len(x)), 1, height, width)
        y = torch.FloatTensor([i for i in batch[:, 1]]).cuda()
        pred = model(x)

        pred = pred.cpu().detach().numpy().reshape(-1)
        pred = np.array([1 if n >= 0.5 else 0 for n in pred])
        return pred


def test_batch(model, criterion, optimizer, batch):
    
    with torch.no_grad():
        
        # forward pass
        x = torch.FloatTensor([i for i in batch[:, 0]]).cuda()
        x = x[:, :, channel_begin: channel_end]
        _, height, width = x.size()
        x = x.view(min(test_size, len(x)), 1, height, width)
        y = np.array([i for i in batch[:, 1]])
        rc = np.array([i for i in batch[:, 2]])

        assert len(np.nonzero(y)[0]) == 2

        pred = model(x)
        
        pred = pred.cpu().detach().numpy().reshape(-1)
        prediction = np.array([1 if n >= 0.5 else 0 for n in pred])

        rc_sort = np.argsort(rc)
        y_sort = y[rc_sort]
        pred_sort = pred[rc_sort]

        # print(y_sort)
        # print(pred_sort)
        # print()

        row_correct = np.argmax(y_sort[:test_size // 2]) == np.argmax(pred_sort[:test_size // 2])
        col_correct = np.argmax(y_sort[test_size // 2:]) == np.argmax(pred_sort[test_size // 2:])
        correct_num = int(row_correct) + int(col_correct)
        is_correct = int(row_correct and col_correct)

        return prediction, pred_sort, y_sort, correct_num, is_correct


def lr_schedule(optimizer, epoch, init_lr):
    lr_anneal = 'pwc'
    if lr_anneal == 'const':
        pass
    elif lr_anneal == 'pwc':
        for param_group in optimizer.param_groups:
            if epoch >=500 and epoch < 800:
                param_group['lr'] = init_lr*0.1
            elif epoch>=800:
                param_group['lr'] = init_lr*0.01



def train(train_data, test_data):
    print(f"learning rate: {learning_rate}, weight decay: {weight_decay}, batch size: {batch_size}")
    # data_size = len(data)

    # 80-20 split train/test
    # cutoff = int(data_size * 80 // 100)
    # cutoff = 600
    # train_data = data[:cutoff]
    # test_data = data[cutoff:]

    # shuffle data
    test_data_size = len(test_data)
    copy_train_data = copy.deepcopy(train_data)
    copy_train_size = len(copy_train_data)
    train_data_size = len(train_data)
    shuffle_idx = np.random.permutation(train_data_size)
    train_data = train_data[shuffle_idx]

    # init model
    model = ConvNet()
    model = model.cuda()

    criterion = weighted_BCE
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    # optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate, weight_decay=weight_decay, momentum=0.9)

    # train loop
    # use k-fold validation
    # k_fold = 10
    k_fold = 1

    # fold_size = int(train_data_size // k_fold)
    fold_size = int(0.2 *  train_data_size)

    collect_train_acc = []
    collect_val_acc = []
    collect_loss = []

    collect_test_acc = []
    collect_test_precision = []
    collect_test_recall = []
    collect_test_fscore = []
    collect_rc_total = []
    collect_correct_total = []
    collect_corr_num = []

    collect_copy_train_acc = []
    collect_copy_train_precision = []
    collect_copy_train_recall = []
    collect_copy_train_fscore = []
    collect_copy_train_rc_total = []
    collect_copy_train_correct_total = []
    collect_copy_train_corr_num = []



    
    for i in range(k_fold):
        # split data into train/val
        # val_data_curr_fold = train_data[i * fold_size:(i + 1) * fold_size]
        # train_data_curr_fold_head = train_data[:i * fold_size]
        # train_data_curr_fold_tail = train_data[(i + 1) * fold_size:]
        # train_data_curr_fold = np.concatenate((train_data_curr_fold_head, train_data_curr_fold_tail))
        train_data_curr_fold = train_data[:-fold_size]
        val_data_curr_fold = train_data[-fold_size:]
        # epoch
        for curr_epoch in range(epoch):
            model = model.train()

            # train minibatch
            train_pred = []
            train_data_curr_fold = train_data_curr_fold[np.random.permutation(len(train_data_curr_fold))]
            # train_data_curr_fold = train_data[:-fold_size]
            # val_data_curr_fold = train_data[-fold_size:]

            losses = 0
            count = 0
            for b in minibatch(train_data_curr_fold, batch_size):
                train_batch_pred, loss = train_batch(model, criterion, optimizer, b, curr_epoch, i)
                losses += loss
                count += 1
                train_pred.append(train_batch_pred)
            losses /= count
            collect_loss.append(losses)
            train_pred = np.concatenate(train_pred, axis=0)

            val_pred = []

            # train中的val,用来看binary clf acc
            model = model.eval()
            for b in minibatch(val_data_curr_fold, batch_size):
                val_batch_pred = val_batch(model, criterion, optimizer, b)
                val_pred.append(val_batch_pred)
            val_pred = np.concatenate(val_pred, axis=0)

            # calculate acc
            train_target = train_data_curr_fold[:, 1].reshape(-1)
            train_acc = cal_acc(train_pred, train_target)
            val_target = val_data_curr_fold[:, 1].reshape(-1)
            val_acc = cal_acc(val_pred, val_target)

            # print stats
            if (curr_epoch + 1) % print_frep == 0:
                print(f"Trainset!! fold: {i + 1}, epoch: {curr_epoch + 1}, train acc: {train_acc}, val acc: {val_acc}, loss: {losses}")

            if curr_epoch == (epoch - 1):
                collect_train_acc.append(train_acc)
                collect_val_acc.append(val_acc)

            # learning rate decay
            lr_schedule(optimizer, epoch, learning_rate)
            # for param_group in optimizer.param_groups:
            #     param_group['lr'] *= 0.9

            # test acc
            model = model.eval()
            test_pred = []
            train_pred = []
            rc_total = 0
            correct_total = 0
            pred_values = []
            corr_num = 0

            for b in minibatch(test_data, test_size):
                test_batch_pred, pred_value, y_sort, rc_count, corr = test_batch(model, criterion, optimizer, b)
                pred_values.append(pred_value)
                if len(pred_values) == 5:
                    mean_value = np.mean(np.array(pred_values), axis=0)
                    row_corr = np.argmax(y_sort[:test_size // 2]) == np.argmax(mean_value[:test_size // 2])
                    col_corr = np.argmax(y_sort[test_size // 2:]) == np.argmax(mean_value[test_size // 2:])
                    # print(mean_value)
                    # print(row_corr)
                    # print(col_corr)
                    corr_num += int(row_corr and col_corr)
                    pred_values = []

                assert rc_count in [0, 1, 2]
                assert corr in [0, 1]
                rc_total += rc_count
                correct_total += corr
                test_pred.append(test_batch_pred)

            test_pred = np.concatenate(test_pred, axis=0)
            test_target = test_data[:, 1].reshape(-1)
            test_acc = cal_acc(test_pred, test_target)
            # print("test_pred:", test_pred)
            # print("test_targ:", test_target)
            test_f_score, test_precision, test_recall = cal_f(test_pred, test_target)

            if (curr_epoch + 1) % print_frep == 0:
                # test_acc: binary acc, rc_correct: 12行列对1个； complete_correct: 12行列对2个; final: pass
                print(f"TestSet! fold: {i + 1}, epoch: {curr_epoch + 1}, test acc: {test_acc}, rc correct: {rc_total}/{int(test_data_size*2/12)}, complete correct: {correct_total}/{int(test_data_size/12)}, final: {corr_num}/2")
                print(f"TestSet! fold: {i + 1}, epoch: {curr_epoch + 1}, test precision: {test_precision}, test recall: {test_recall}, test f score: {test_f_score}")

            collect_test_acc.append(test_acc)
            collect_test_precision.append(test_precision)
            collect_test_recall.append(test_recall)
            collect_test_fscore.append(test_f_score)
            collect_rc_total.append(rc_total)
            collect_correct_total.append(correct_total)
            collect_corr_num.append(corr_num)

            # if corr_num >= 1:
            #     # 保存模型
            #     save_ckpt(i, model, optimizer, is_nice=True)

            # copy train
            copy_train_pred = []
            rc_total = 0
            correct_total = 0
            pred_values = []
            corr_num = 0
            for c in minibatch(copy_train_data, test_size):
                copy_train_batch_pred, pred_value, y_sort, rc_count, corr = test_batch(model, criterion, optimizer, c)
                pred_values.append(pred_value)

                if len(pred_values) == 5:
                    mean_value = np.mean(np.array(pred_values), axis=0)
                    row_corr = np.argmax(y_sort[:test_size // 2]) == np.argmax(mean_value[:test_size // 2])
                    col_corr = np.argmax(y_sort[test_size // 2:]) == np.argmax(mean_value[test_size // 2:])
                    # print(mean_value)
                    # print(row_corr)
                    # print(col_corr)
                    corr_num += int(row_corr and col_corr)
                    pred_values = []

                assert rc_count in [0, 1, 2]
                assert corr in [0, 1]
                rc_total += rc_count
                correct_total += corr
                copy_train_pred.append(copy_train_batch_pred)

            copy_train_pred = np.concatenate(copy_train_pred, axis=0)
            copy_train_target = copy_train_data[:, 1].reshape(-1)
            copy_train_acc = cal_acc(copy_train_pred, copy_train_target)
            # print("test_pred:", test_pred)
            # print("test_targ:", test_target)
            copy_train_f_score, copy_train_precision, copy_train_recall = cal_f(copy_train_pred, copy_train_target)

            if (curr_epoch + 1) % print_frep == 0:
                # test_acc: binary acc, rc_correct: 12行列对1个； complete_correct: 12行列对2个; final: pass
                print(f"CopyTrainSet! fold: {i + 1}, epoch: {curr_epoch + 1}, copy_train_acc  acc: {copy_train_acc }, rc correct: {rc_total}/{int(copy_train_size*2/12)}, complete correct: {correct_total}/{int(copy_train_size/12)}, final: {corr_num}/2")
                print(f"CopyTrainSet! fold: {i + 1}, epoch: {curr_epoch + 1}, copy_train precision: {copy_train_precision}, copy_train recall: {copy_train_recall}, copy_train f score: {copy_train_f_score}")


            collect_copy_train_acc.append(copy_train_acc)
            collect_copy_train_precision.append(copy_train_precision)
            collect_copy_train_recall.append(copy_train_recall)
            collect_copy_train_fscore.append(copy_train_f_score)

            collect_copy_train_rc_total.append(rc_total)
            collect_copy_train_correct_total.append(correct_total)
            collect_copy_train_corr_num.append(corr_num)

    save_ckpt(i, model, optimizer, is_nice=False)

    plt.figure()
    plt.title('Final acc')
    plt.plot(range(epoch), np.array(collect_copy_train_rc_total)/100.0, label='train_rc_total')
    plt.plot(range(epoch), np.array(collect_copy_train_correct_total)/50.0, label='train_correct_total')
    plt.plot(range(epoch), np.array(collect_rc_total)/20.0, label='test_rc_total')
    plt.plot(range(epoch), np.array(collect_correct_total)/10.0, label='test_correct_total')
    plt.legend()
    plt.savefig('final_acc.png')
    plt.show()

    # plt.figure()
    # plt.title('Test acc, Total %d' % int(len(test_data)/12))
    # plt.plot(range(len(collect_rc_total)), collect_rc_total, label='rc_total')
    # plt.plot(range(len(collect_correct_total)), collect_correct_total, label='correct_total')
    # plt.legend()
    # plt.savefig('test_acc.png')
    # plt.show()

    plt.figure()
    plt.title('Test index')
    plt.plot(range(epoch), collect_test_acc, label='bi_acc')
    plt.plot(range(epoch), collect_test_precision, label='precision')
    plt.plot(range(epoch), collect_test_recall, label='recall')
    plt.plot(range(epoch), collect_test_fscore, label='fscore')
    plt.legend()
    plt.savefig('test_index.png')
    plt.show()
    
    plt.figure()
    plt.title('Train loss')
    plt.plot(range(epoch), collect_loss)
    plt.savefig('train_loss.png')
    plt.show()

    # plt.figure()
    # plt.title('Leaning rate')
    # plt.plot(range(epoch), collect_loss)
    # plt.savefig('train_loss.png')
    # plt.show()



    average_train_acc = np.mean(np.array(collect_train_acc))
    average_val_acc = np.mean(np.array(collect_val_acc))
    average_test_acc = np.mean(np.array(collect_test_acc))
    average_test_precision = np.mean(np.array(collect_test_precision))
    average_test_recall = np.mean(np.array(collect_test_recall))
    average_test_fscore = np.mean(np.array(collect_test_fscore))
    print(f"average_train_acc: {average_train_acc}")
    print(f"average_val_acc: {average_val_acc}")
    print(f"average_test_acc: {average_test_acc}")
    print(f"average_test_precision: {average_test_precision}")
    print(f"average_test_recall: {average_test_recall}")
    print(f"average_test_fscore: {average_test_fscore}")


def save_ckpt(fold, model, optimizer, is_nice=False):
    """Save checkpoint"""
    output_dir = './results'
    ckpt_dir = os.path.join(output_dir, 'ckpt' + str(subject_num))
    if not os.path.exists(ckpt_dir):
        os.makedirs(ckpt_dir)

    string = '_nice' if is_nice else '_rubbish'
    save_name = os.path.join(ckpt_dir, 'model{}.pth'.format(string))

    torch.save({
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict()}, save_name)

    print('save model: %s' % save_name)


def test(data, ckpt_path):
    model = ConvNet()
    model.load_state_dict(torch.load(ckpt_path))
    model.eval()


if __name__ == '__main__':

    # data format: [(x, y, y_stimulate)]
    is_with_average = '' if is_with_ave == 'w' else 'o'
    train_or_test = 'train' if is_train == 1 else 'test'

    if is_train == 1:
        data_train = np.zeros((0, 3), dtype=float)
        data_val = np.zeros((0, 3), dtype=float)
        # for i in range():
        print("开始训练被试%d..." % subject_num)
        with open(join(data_path, f"s{subject_num}_{train_or_test}_w{is_with_average}.pkl"), "rb") as infile:
            temp = pickle.load(infile)['data']
            data_train = np.vstack((data_train, temp[:-120]))
            data_val = np.vstack((data_val, temp[-120:]))  # 2个字符
        # print
        train(data_train, data_val)  # 600, 120
    else:
        # test(data)
        pass
