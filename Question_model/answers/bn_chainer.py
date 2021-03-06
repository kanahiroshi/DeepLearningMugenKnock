import chainer
import chainer.links as L
import chainer.functions as F
import argparse
import cv2
import numpy as np
from glob import glob

num_classes = 2
img_height, img_width = 224, 224
GPU = -1

class VGG16(chainer.Chain):
    def __init__(self, train=True):
        self.train = train
        super(VGG16, self).__init__()
        with self.init_scope():
            # block conv1
            self.conv1 = chainer.Sequential()
            for i in range(2):
                self.conv1.append(L.Convolution2D(None, 64, ksize=3, pad=1, stride=1, nobias=False))
                self.conv1.append(F.relu)
                self.conv1.append(L.BatchNormalization(64))
                
            # block conv2
            self.conv2 = chainer.Sequential()
            for i in range(2):
                self.conv2.append(L.Convolution2D(None, 128, ksize=3, pad=1, stride=1, nobias=False))
                self.conv2.append(F.relu)
                self.conv2.append(L.BatchNormalization(128))
                
            # block conv3
            self.conv3 = chainer.Sequential()
            for i in range(3):
                self.conv3.append(L.Convolution2D(None, 256, ksize=3, pad=1, stride=1, nobias=False))
                self.conv3.append(F.relu)
                self.conv3.append(L.BatchNormalization(256))
                
            # block conv4
            self.conv4 = chainer.Sequential()
            for i in range(3):
                self.conv4.append(L.Convolution2D(None, 512, ksize=3, pad=1, stride=1, nobias=False))
                self.conv4.append(F.relu)
                self.conv4.append(L.BatchNormalization(512))
                
            # block conv1
            self.conv5 = chainer.Sequential()
            for i in range(3):
                self.conv5.append(L.Convolution2D(None, 512, ksize=3, pad=1, stride=1, nobias=False))
                self.conv5.append(F.relu)
                self.conv5.append(L.BatchNormalization(512))
            
            self.fc1 = L.Linear(None, 4096, nobias=False)
            self.fc2 = L.Linear(None, 4096, nobias=False)
            self.fc_out = L.Linear(None, num_classes, nobias=False)

    def __call__(self, x):
        # block conv1
        x = self.conv1(x)
        x = F.max_pooling_2d(x, ksize=2, stride=2)
        
        # block conv2
        x = self.conv2(x)
        x = F.max_pooling_2d(x, ksize=2, stride=2)

        # block conv3
        x = self.conv3(x)
        x = F.max_pooling_2d(x, ksize=2, stride=2)

        # block conv4
        x = self.conv4(x)
        x = F.max_pooling_2d(x, ksize=2, stride=2)

        # block conv5
        x = self.conv5(x)
        x = F.max_pooling_2d(x, ksize=2, stride=2)

        x = F.relu(self.fc1(x))
        x = F.dropout(x)
        x = F.relu(self.fc2(x))
        x = F.dropout(x)
        x = self.fc_out(x)
        return x


CLS = ['akahara', 'madara']

# get train data
def data_load(path, hf=False, vf=False):
    xs = []
    ts = []
    paths = []
    
    for dir_path in glob(path + '/*'):
        for path in glob(dir_path + '/*'):
            x = cv2.imread(path)
            x = cv2.resize(x, (img_width, img_height)).astype(np.float32)
            x /= 255.
            xs.append(x)

            for i, cls in enumerate(CLS):
                if cls in path:
                    t = i
            
            ts.append(t)

            paths.append(path)

            if hf:
                xs.append(x[:, ::-1])
                ts.append(t)
                paths.append(path)

            if vf:
                xs.append(x[::-1])
                ts.append(t)
                paths.append(path)

            if hf and vf:
                xs.append(x[::-1, ::-1])
                ts.append(t)
                paths.append(path)

    xs = np.array(xs, dtype=np.float32)
    ts = np.array(ts, dtype=np.int)
    
    xs = xs.transpose(0,3,1,2)

    return xs, ts, paths

# train
def train():
    # model
    model = VGG16(train=True)

    if GPU >= 0:
        chainer.cuda.get_device(GPU).use()
        model.to_gpu()
    
    opt = chainer.optimizers.MomentumSGD(0.01, momentum=0.9)
    opt.setup(model)
    opt.add_hook(chainer.optimizer.WeightDecay(0.0005))

    xs, ts, _ = data_load('../Dataset/train/images/', hf=True, vf=True)

    # training
    mb = 8
    mbi = 0
    train_ind = np.arange(len(xs))
    np.random.seed(0)
    np.random.shuffle(train_ind)
    
    for i in range(500):
        if mbi + mb > len(xs):
            mb_ind = train_ind[mbi:]
            np.random.shuffle(train_ind)
            mb_ind = np.hstack((mb_ind, train_ind[:(mb-(len(xs)-mbi))]))
            mbi = mb - (len(xs) - mbi)
        else:
            mb_ind = train_ind[mbi: mbi+mb]
            mbi += mb

        x = xs[mb_ind]
        t = ts[mb_ind]
            
        if GPU >= 0:
            x = chainer.cuda.to_gpu(x)
            t = chainer.cuda.to_gpu(t)
        #else:
        #    x = chainer.Variable(x)
        #    t = chainer.Variable(t)

        y = model(x)

        loss = F.softmax_cross_entropy(y, t)
        accu = F.accuracy(y, t)

        model.cleargrads()
        loss.backward()
        opt.update()

        loss = loss.data
        accu = accu.data
        if GPU >= 0:
            loss = chainer.cuda.to_cpu(loss)
            accu = chainer.cuda.to_cpu(accu)
        
        print("iter >>", i+1, ',loss >>', loss.item(), ',accuracy >>', accu)

    chainer.serializers.save_npz('cnn.npz', model)

# test
def test():
    model = VGG16(train=False)

    if GPU >= 0:
        chainer.cuda.get_device_from_id(cf.GPU).use()
        model.to_gpu()

    ## Load pretrained parameters
    chainer.serializers.load_npz('cnn.npz', model)

    xs, ts, paths = data_load('../Dataset/test/images/')

    for i in range(len(paths)):
        x = xs[i]
        t = ts[i]
        path = paths[i]
        x = np.expand_dims(x, axis=0)
        
        if GPU >= 0:
            x = chainer.cuda.to_gpu(x)
            
        pred = model(x).data
        pred = F.softmax(pred)

        if GPU >= 0:
            pred = chainer.cuda.to_cpu(pred)
                
        pred = pred[0].data
                
        print("in {}, predicted probabilities >> {}".format(path, pred))
    

def arg_parse():
    parser = argparse.ArgumentParser(description='CNN implemented with Keras')
    parser.add_argument('--train', dest='train', action='store_true')
    parser.add_argument('--test', dest='test', action='store_true')
    args = parser.parse_args()
    return args

# main
if __name__ == '__main__':
    args = arg_parse()

    if args.train:
        train()
    if args.test:
        test()

    if not (args.train or args.test):
        print("please select train or test flag")
        print("train: python main.py --train")
        print("test:  python main.py --test")
        print("both:  python main.py --train --test")
