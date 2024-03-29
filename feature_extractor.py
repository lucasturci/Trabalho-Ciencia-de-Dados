import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Activation, Conv2D, Dropout, Flatten, Input, MaxPooling2D
from tensorflow.keras.applications import vgg16

import os
from glob import glob
import shutil
import numpy as np



# cria modelo keras com pesos do arquivo vgg_face_weights.h5
# cria outro modelo chamado extractor_model, a partir do vgg_model, cujos outputs sao camadas intermediarias do primeiro
# retorna o extractor_model
def get_feature_extractor(vgg_weights_filepath="vgg_face_weights.h5"):
    model_in = Input(shape=(224, 224, 3))

    model = Conv2D(64, (3, 3), padding='same', activation='relu')(model_in)
    model = Conv2D(64, (3, 3), padding='same', activation='relu')(model)
    model = MaxPooling2D((2, 2), strides=(2, 2))(model)

    model = Conv2D(128, (3, 3), padding='same', activation='relu')(model)
    model = Conv2D(128, (3, 3), padding='same', activation='relu')(model)
    model = MaxPooling2D((2, 2), strides=(2, 2))(model)

    model = Conv2D(256, (3, 3), padding='same', activation='relu')(model)
    model = Conv2D(256, (3, 3), padding='same', activation='relu')(model)
    model = Conv2D(256, (3, 3), padding='same', activation='relu')(model)
    model = MaxPooling2D((2, 2), strides=(2, 2))(model)

    model = Conv2D(512, (3, 3), padding='same', activation='relu')(model)
    model = Conv2D(512, (3, 3), padding='same', activation='relu')(model)
    model = Conv2D(512, (3, 3), padding='same', activation='relu')(model)
    model = MaxPooling2D((2, 2), strides=(2, 2))(model)

    model = Conv2D(512, (3, 3), padding='same', activation='relu')(model)
    model = Conv2D(512, (3, 3), padding='same', activation='relu')(model)
    model = Conv2D(512, (3, 3), padding='same', activation='relu')(model)
    model = MaxPooling2D((2, 2), strides=(2, 2))(model)

    model_dense_0 = Conv2D(4096, (7, 7), padding='valid', activation='relu')(model)
    model_dense_0 = Dropout(0.5)(model_dense_0)

    model_dense_1 = Conv2D(4096, (1, 1), padding='valid', activation='relu')(model_dense_0)
    model_dense_1 = Dropout(0.5)(model_dense_1)

    model_dense_2 = Conv2D(2622, (1, 1), padding='valid')(model_dense_1)
    model_dense_2 = Flatten()(model_dense_2)

    model_out = Activation('softmax')(model_dense_2)

    vgg_model = Model(model_in, model_out)
    vgg_model.load_weights(vgg_weights_filepath)

    extract_dense_0 = Flatten()(model_dense_0)
    extract_dense_1 = Flatten()(model_dense_1)
    extract_dense_2 = model_dense_2

    extractor_model = Model(model_in, [extract_dense_0, extract_dense_1, extract_dense_2])

    return extractor_model

def get_generator(dir, batch_size=256, image_size=(224, 224),
                preprocessing_function=vgg16.preprocess_input, rescale=None):
    gen_args = dict(featurewise_center=False,
                    samplewise_center=False,
                    featurewise_std_normalization=False,
                    samplewise_std_normalization=False,
                    zca_whitening=False,
                    zca_epsilon=1e-06,
                    rotation_range=0.0,
                    width_shift_range=0.0,
                    height_shift_range=0.0,
                    brightness_range=None,
                    shear_range=0.0,
                    zoom_range=0.0,
                    channel_shift_range=0.0,
                    fill_mode='nearest',
                    cval=0.0,
                    horizontal_flip=False,
                    vertical_flip=False,
                    rescale=rescale,
                    preprocessing_function=preprocessing_function,
                    data_format='channels_last',
                    validation_split=0.0,
                    dtype=None)

    flow_args = dict(target_size=image_size,
                    color_mode='rgb',
                    classes=None,
                    class_mode='binary',
                    batch_size=batch_size,
                    shuffle=False,
                    seed=500,
                    save_to_dir=None,
                    save_prefix="",
                    save_format='jpg',
                    follow_links=False,
                    subset=None,
                    interpolation='bicubic')

    datagen = ImageDataGenerator(**gen_args).flow_from_directory(dir, **flow_args)
    return datagen

def extract_all(in_dir, out_dir, vgg_weights_filepath="vgg_face_weights.h5"):
    extractor = get_feature_extractor(vgg_weights_filepath)
    generator = get_generator(in_dir)

    if any([os.path.exists(os.path.join(out_dir, "layer_{}".format(i))) for i in range(len(extractor.output))]):
        print("Removing all \'layer_*\' directorys from output directory. Continue? [y/n]")
        if input().lower() == 'y':
            print("Deleting...")
            for i in range(len(extractor.output)):
                rm_dir = os.path.join(out_dir, "layer_{}".format(i))
                if os.path.exists(rm_dir):
                    shutil.rmtree(rm_dir)
        else:
            print("Aborting...")
            return

    folds_files = [fold_file.split(os.sep)[-1] for fold_file in glob(os.path.join(in_dir, "fold_*.txt"))]
    for i in range(len(extractor.output)):
        cur_out_dir = os.path.join(out_dir, "layer_{}".format(i))
        os.makedirs(cur_out_dir)
        for fold_file in folds_files:
            shutil.copyfile(os.path.join(in_dir, fold_file), os.path.join(cur_out_dir, fold_file))

    classes_map = {val : key for key, val in generator.class_indices.items()}
    for _ in range(len(generator)):
        x, y = generator.next()
        outs = extractor.predict(x)
        for layer in range(len(extractor.output)):
            for cur_sample, cur_class in zip(outs[layer], y):
                cur_out_file = os.path.join(out_dir, "layer_{}".format(layer), classes_map[cur_class]+".npy")
                if os.path.isfile(cur_out_file):
                    cur_arr = np.load(cur_out_file)
                    cur_arr = np.concatenate((cur_arr, np.expand_dims(cur_sample, axis=0)), axis=0)
                else:
                    cur_arr = np.expand_dims(cur_sample, axis=0)
                np.save(cur_out_file, cur_arr)



if __name__ == '__main__':
    extract_all("dataset", "extracted")