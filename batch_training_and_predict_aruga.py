# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt
from model import ESN, Tikhonov, RLS, Pseudoinv
import sys
import os
import csv
import re
import datetime
import pickle
import argparse
from matplotlib.widgets import RadioButtons
from matplotlib.widgets import CheckButtons


np.random.seed(seed=0)

PARAM_OPT = ["tikhonov", "rls"]
PARAM_RLS = "rls"

parser = argparse.ArgumentParser(description='Hyper parameter.')
parser.add_argument('-csv_file', dest='csv_file', type=str, help='target data', required=True)
parser.add_argument('-save_dir', dest='save_dir', default='output', type=str, help='Directory for output files')
parser.add_argument('-is_save_chart', dest='is_save_chart', default=True, type=bool, help='Save a chart if True')
parser.add_argument('-is_show_chart', dest='is_show_chart', default=True, type=bool, help='Show a chart if True')



def save_object(file_name, data):
    with open(file_name, 'wb') as f:
        pickle.dump(data, f) #保存

def is_utf8_file_with_bom(filename):
    '''utf-8 ファイルが BOM ありかどうかを判定する
    '''
    line_first = open(filename, encoding='utf-8').readline()
    return (line_first[0] == '\ufeff')

# データの読み込み
def read_csv_data(file_name):
    '''
    :入力：データファイル名, file_name
    :出力：データ, data
    '''
    data = np.empty(0)
    is_with_bom = is_utf8_file_with_bom(file_name)
    encoding = 'utf-8-sig' if is_with_bom else 'utf-8'
    with open(file_name, 'r',encoding=encoding) as f:
        reader = csv.reader(f)
        data_list = list(reader)[1:] #Aruga add "[1:]"
        print('data_num:', len(data_list))
    #print('data_list',data_list)
    data = np.array(data_list, dtype=float)

    return data


# 出力のスケーリング
class ScalingShift:
    def __init__(self, scale, shift):
        '''
        :param scale: 出力層のスケーリング（scale[n]が第n成分のスケーリング）
        :param shift: 出力層のシフト（shift[n]が第n成分のシフト）
        '''
        self.scale = np.diag(scale)
        self.shift = np.array(shift)
        self.inv_scale = np.linalg.inv(self.scale)
        self.inv_shift = -np.dot(self.inv_scale, self.shift)

    def __call__(self, x):
        return np.dot(self.scale, x) + self.shift

    def inverse(self, x):
        return np.dot(self.inv_scale, x) + self.inv_shift


def moving_average(x, w):
    x_t = x.T
    data = []
    for d in x_t:
        avg = np.convolve(d, np.ones(w), 'valid') / w
        data.append(np.append(avg, np.zeros(w-1)))

    return np.array(data).T

def get_title_from_params(parametes):

    members = [attr for attr in vars(parametes).items()]

    title = []
    used_words = []
    for member in members:
        name = member[0]
        value = member[1]

        param_name = ''
        for c in name:
            param_name += c
            if param_name not in used_words:
                break

        used_words.append(param_name)

        title.append( param_name + str(value) )

    return "-".join(title)

def get_valid_argumented_data_from_rawdata(app, raw_data):
    data = []
    for raw_value in raw_data:
        pulses, labels = app.prepare_data(raw_value)
        data.append(pulses + labels)
    data = np.array(data)
    return data


def main(app):
    # Set hyper parametes and custom parameters for the application
    parametes = app.Parameters(parser)
    training_app = app.TrainingApp(parametes)

    title = get_title_from_params(parametes)

    # 出力のスケーリング関数
    output_func = ScalingShift([1.0], [1.0])

    # Create model with the hyper parameters
    model = ESN(parametes.num_of_input_data, 
                parametes.num_of_output_classes, 
                parametes.node, 
                density=parametes.density,
                input_scale=parametes.input_scale,
                rho=parametes.rho,
                fb_scale=parametes.fb_scale,
                leaking_rate=parametes.leaking_rate,
                classification = parametes.no_class, 
                average_window=parametes.average_window)


    optimizer = Tikhonov(parametes.node, parametes.num_of_output_classes, 0.1)


    raw_data = read_csv_data(csv_file)

    data = get_valid_argumented_data_from_rawdata(training_app, raw_data)

    if len(data) == 0:
        print('csv data is None')
        exit(0)

    # 訓練データ，検証データの割合
    n_wave_train = 0.6 # トレーニング6割
    n_wave_test = 1 - n_wave_train

    gt_dim = len(data[0]) - parametes.num_of_input_data

    # 時系列入力データ
    period = 100

    u = data[:, :parametes.num_of_input_data]
    d = data[:, parametes.num_of_input_data:].reshape(-1, gt_dim)
    #d = data[:, parametes.num_of_input_data]
    T = int(len(d) * n_wave_train)

    # 訓練・検証用情報
    train_U = u[:T].reshape(-1, parametes.num_of_input_data)
    train_D = d[:T]

    test_U = u[T:].reshape(-1, parametes.num_of_input_data)
    test_D = d[T:]


    # 学習（リッジ回帰）
    now = datetime.datetime.now()
    train_Y = model.train(train_U, train_D, optimizer) 
    print('traing time:', datetime.datetime.now() - now)

    save_object('model.pkl',model)

    # 訓練データに対するモデル出力
    test_Y = model.predict(test_U)

    m_avg = 1
    test_Y = moving_average(test_Y,m_avg)
    train_Y2 = model.predict(train_U)

    ###
    test_y_bool = np.where(test_Y >= 0.5, 1, 0)
    test_y_bool_row_sum = np.sum(test_y_bool, axis = 1) # 行方向のsumで0ならば正解なし or 0
    test_d_bool = np.where(test_D >= 0.5, 1, 0)
    test_d_bool_nega = np.where(test_D < 0.5, 1, 0)
    test_d_bool_row_sum = np.sum(test_d_bool, axis = 1)
    test_d_bool_bin = np.where(test_d_bool_row_sum == 0, 0, 1)
    test_d_bool_bin_nega = np.where(test_d_bool_row_sum == 0, 1, 0)

    eval = np.zeros(test_y_bool.shape[0])

    for i in range(test_y_bool.shape[0]):
        if test_y_bool_row_sum[i] == 0: # すべて0.5未満
            eval[i] = (test_d_bool_row_sum[i] == 0) # 0なら正解をセット
        else:
            max = 0
            for j in range(test_y_bool.shape[1]): # クラスのパターン数
                if test_y_bool[i, max] < test_y_bool[i, j]:
                    max = j
            eval[i] = (test_d_bool[i, max] == 1) # 最大値のクラスが1なら正解をセット

    if np.count_nonzero(test_d_bool_bin) == 0:
        accuracy_one = 0
    else:
        accuracy_one = np.count_nonzero(eval * test_d_bool_bin) / np.count_nonzero(test_d_bool_bin)
    if np.count_nonzero(test_d_bool_bin_nega) == 0:
        accuracy_zero = 0
    else:
        accuracy_zero = np.count_nonzero(eval * test_d_bool_bin_nega) / np.count_nonzero(test_d_bool_bin_nega)
    accuracy = accuracy_one * accuracy_zero
    print('moving average window size:',m_avg)
    print('accuracy:',accuracy)
    print('accuracy_one:',accuracy_one)
    print('accuracy_zero:',accuracy_zero)


    ###

    target = test_D[0:int(period * n_wave_test * 100 / gt_dim):period, gt_dim - 1]

    disp_train_width = int(len(d) * n_wave_train)
    disp_test_width = int(len(d) * n_wave_test)

    # グラフ表示用データ
    T_disp = (-disp_train_width, disp_test_width)
    t_axis = np.arange(T_disp[0], T_disp[1])  # 時間軸
    disp_U = np.concatenate((train_U[T_disp[0]:], test_U[:T_disp[1]])) 
    disp_D = np.concatenate((train_D[T_disp[0]:], test_D[:T_disp[1]]))
    disp_Y = np.concatenate((train_Y2[T_disp[0]:], test_Y[:T_disp[1]]))

    # グラフ表示
    plt.rcParams['font.size'] = 10
    fig = plt.figure(figsize = (40, 12), dpi=240)
    plt.subplots_adjust(hspace = 0.3)

    graph_name = title + '-mva' + str(m_avg) + '-acc'+ str('{:.2f}'.format(accuracy_one*100))  \
                                             + 'x'   + str('{:.2f}'.format(accuracy_zero*100)) \
                                             + '='   + str('{:.2f}'.format(accuracy*100))
    rax = plt.axes([0.9, 0.4, 0.1, 0.3])
    labels = ['labels','predicts','pred. bin','TP','TN','FN','FP']
    visibility = [True,True,True,True]
    check = CheckButtons(rax, labels, visibility)
    def func(label):
        index = labels.index(label)
        for i in range(gt_dim):
            lines[i][index][0].set_visible(not lines[i][index][0].get_visible())
            plt.draw()
    check.on_clicked(func)


    sensors = ['Right thumb','Left thumb','Left middle finger']
    for i in range(parametes.num_of_input_data):

        ax = fig.add_subplot(parametes.num_of_input_data + gt_dim, 1, i + 1)
        if i == 0:
            ax.text(-0.1, 1, '(a)', transform=ax.transAxes)
            ax.text(0.2, 1.05, 'Training', transform=ax.transAxes)
            ax.text(0.7, 1.05, 'Testing', transform=ax.transAxes)
        ax.plot(t_axis, disp_U[:, i*2], color='blue')
        plt.ylabel('input #'+ str(i))
        plt.axvline(x=0, ymin=0, ymax=1, color='gray', linestyle=':')



    plt.suptitle(graph_name, fontsize=9)
    buttons = ['up','down','left','right']
    lines=[]
    for i in range(gt_dim):
        ax = fig.add_subplot(parametes.num_of_input_data + gt_dim, 1, parametes.num_of_input_data + i + 1)
        l0 = ax.plot(t_axis, disp_D[:,i], color='gray', linestyle='-', label='labels', linewidth=1)
        l1 = ax.plot(t_axis, disp_Y[:,i], color='orange', linestyle='-', label='predicts', linewidth=1)
        l2 = ax.plot(t_axis, np.where(disp_Y[:,i]>0.5,0.8,0), color='green', linestyle='-', label='pred. bin', linewidth=1)
        t = np.array([1 if x == y else 0 for (x, y) in zip(disp_D[:,i], np.where(disp_Y[:,i]>0.5,1,0))])
        tp = np.array([1 if (x == 1) & (y == 1) else 0 for (x, y) in zip(disp_D[:,i], np.where(disp_Y[:,i]>0.5,1,0))])
        tn = np.array([1 if (x == 0) & (y == 0) else 0 for (x, y) in zip(disp_D[:,i], np.where(disp_Y[:,i]>0.5,1,0))])
        fn = np.array([1 if (x == 1) & (y == 0) else 0 for (x, y) in zip(disp_D[:,i], np.where(disp_Y[:,i]>0.5,1,0))])
        fp = np.array([1 if (x == 0) & (y == 1) else 0 for (x, y) in zip(disp_D[:,i], np.where(disp_Y[:,i]>0.5,1,0))])
        l4 = ax.plot(t_axis, np.where(tn==1, 1.1,None) , color='red', linestyle='-', label='TN', linewidth=1)
        l3 = ax.plot(t_axis, np.where(tp==1, 1.1,None) , color='blue', linestyle='-', label='TP', linewidth=1)
        l6 = ax.plot(t_axis, np.where(fp==1,-0.1,None) , color='red', linestyle='-', label='FP', linewidth=1)
        l5 = ax.plot(t_axis, np.where(fn==1,-0.1,None) , color='blue', linestyle='-', label='FN', linewidth=1)
        precision = len(np.where(tp==1)) / (len(np.where(tp==1))+len(np.where(fp==1)))
        recall = len(np.where(tp==1)) / (len(np.where(tp==1)) + len(np.where(fn==1)))
        ax.set_ylabel('class #' + str(i))

        ax.axvline(x=0, ymin=0, ymax=1, color='k', linestyle='--', linewidth=1)
        ax.axhline(y=0.5, xmin=0, xmax=1, color='k', linestyle='--', linewidth=1)
        lines.append((l0,l1,l2,l3,l4,l5,l6))

    save_name = os.path.join(params.save_dir, graph_name + '.png')

    if params.is_save_chart:
        plt.savefig(save_name)

    if params.is_show_chart:
        plt.show()

    plt.clf()
    plt.close()


def run(*_args):
    print('_args',_args)
    params = parser.parse_args(_args)

    if not os.path.exists(params.save_dir):
        # ディレクトリが存在しない場合、ディレクトリを作成する
        os.makedirs(params.save_dir)

    main(params.target_data, params)

import app_thumbup

if __name__ == '__main__':
    params = parser.parse_args()

    # Set parametes as global variable
    csv_file = params.csv_file
    save_dir = params.save_dir

    # Make directory if not exist
    os.makedirs(save_dir, exist_ok=True)

    # make csv and model file names
    now = datetime.datetime.now()
    out_model_filename = os.path.join(save_dir, 'model_' + now.strftime('%Y%m%d_%H%M%S') + '.pkl')

    # Set application class
    #app = app_famicom
    #app = app_balloon
    app = app_thumbup

    try:
        main(app)
    except KeyboardInterrupt:
        print('closeing...')
    exit()

