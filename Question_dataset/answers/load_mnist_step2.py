import os
import gzip
import numpy as np
import matplotlib.pyplot as plt

def load_mnist():
    dir_path = "mnist_datas"

    files = ["train-images-idx3-ubyte.gz",
             "train-labels-idx1-ubyte.gz",
             "t10k-images-idx3-ubyte.gz",
             "t10k-labels-idx1-ubyte.gz"]

    # download mnist datas
    if not os.path.exists(dir_path):

        os.makedirs(dir_path)

        data_url = "http://yann.lecun.com/exdb/mnist/"

        for file_url in files:

            after_file = file_url.split('.')[0]
            
            if os.path.exists(dir_path + '/' + after_file):
                continue
            
            os.system("wget {}/{}".format(data_url, file_url))
            os.system("mv {} {}".format(file_url, dir_path))

        
    # load mnist data

    # load train data
    with gzip.open(dir_path + '/' + files[0], 'rb') as f:
        train_x = np.frombuffer(f.read(), np.uint8, offset=16)
        train_x = train_x.astype(np.float32)
        train_x = train_x.reshape((-1, 28, 28))
        print("train images >>", train_x.shape)

    with gzip.open(dir_path + '/' + files[1], 'rb') as f:
        train_y = np.frombuffer(f.read(), np.uint8, offset=8)
        print("train labels >>", train_y.shape)


load_mnist()
