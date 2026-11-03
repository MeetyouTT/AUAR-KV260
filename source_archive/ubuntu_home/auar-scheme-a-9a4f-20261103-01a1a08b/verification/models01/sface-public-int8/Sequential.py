# GENETARED BY NNDCT, DO NOT EDIT!

import torch
from torch import tensor
import pytorch_nndct as py_nndct

class Sequential(py_nndct.nn.NndctQuantModel):
    def __init__(self):
        super(Sequential, self).__init__()
        self.module_0 = py_nndct.nn.Input() #Sequential::input_0
        self.module_1 = py_nndct.nn.Conv2d(in_channels=3, out_channels=32, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_1_conv2d]/input.3
        self.module_2 = py_nndct.nn.Conv2d(in_channels=32, out_channels=32, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=32, bias=False) #Sequential::Sequential/ResidualPRelu[conv_1_relu]/Conv2d[negative]/input.7
        self.module_3 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_1_relu]/ReLU[relu]/input.9
        self.module_4 = py_nndct.nn.Conv2d(in_channels=32, out_channels=32, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=32, bias=False) #Sequential::Sequential/ResidualPRelu[conv_1_relu]/Conv2d[slope]/5853
        self.module_5 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_1_relu]/input.11
        self.module_6 = py_nndct.nn.Conv2d(in_channels=32, out_channels=32, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=32, bias=True) #Sequential::Sequential/Conv2d[conv_2_dw_conv2d]/input.13
        self.module_7 = py_nndct.nn.Conv2d(in_channels=32, out_channels=32, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=32, bias=False) #Sequential::Sequential/ResidualPRelu[conv_2_dw_relu]/Conv2d[negative]/input.17
        self.module_8 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_2_dw_relu]/ReLU[relu]/input.19
        self.module_9 = py_nndct.nn.Conv2d(in_channels=32, out_channels=32, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=32, bias=False) #Sequential::Sequential/ResidualPRelu[conv_2_dw_relu]/Conv2d[slope]/5921
        self.module_10 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_2_dw_relu]/input.21
        self.module_11 = py_nndct.nn.Conv2d(in_channels=32, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_2_conv2d]/input.23
        self.module_12 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=64, bias=False) #Sequential::Sequential/ResidualPRelu[conv_2_relu]/Conv2d[negative]/input.27
        self.module_13 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_2_relu]/ReLU[relu]/input.29
        self.module_14 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=64, bias=False) #Sequential::Sequential/ResidualPRelu[conv_2_relu]/Conv2d[slope]/5989
        self.module_15 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_2_relu]/input.31
        self.module_16 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[2, 2], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #Sequential::Sequential/Conv2d[conv_3_dw_conv2d]/input.33
        self.module_17 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=64, bias=False) #Sequential::Sequential/ResidualPRelu[conv_3_dw_relu]/Conv2d[negative]/input.37
        self.module_18 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_3_dw_relu]/ReLU[relu]/input.39
        self.module_19 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=64, bias=False) #Sequential::Sequential/ResidualPRelu[conv_3_dw_relu]/Conv2d[slope]/6057
        self.module_20 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_3_dw_relu]/input.41
        self.module_21 = py_nndct.nn.Conv2d(in_channels=64, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_3_conv2d]/input.43
        self.module_22 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=128, bias=False) #Sequential::Sequential/ResidualPRelu[conv_3_relu]/Conv2d[negative]/input.47
        self.module_23 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_3_relu]/ReLU[relu]/input.49
        self.module_24 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=128, bias=False) #Sequential::Sequential/ResidualPRelu[conv_3_relu]/Conv2d[slope]/6125
        self.module_25 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_3_relu]/input.51
        self.module_26 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=128, bias=True) #Sequential::Sequential/Conv2d[conv_4_dw_conv2d]/input.53
        self.module_27 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=128, bias=False) #Sequential::Sequential/ResidualPRelu[conv_4_dw_relu]/Conv2d[negative]/input.57
        self.module_28 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_4_dw_relu]/ReLU[relu]/input.59
        self.module_29 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=128, bias=False) #Sequential::Sequential/ResidualPRelu[conv_4_dw_relu]/Conv2d[slope]/6193
        self.module_30 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_4_dw_relu]/input.61
        self.module_31 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_4_conv2d]/input.63
        self.module_32 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=128, bias=False) #Sequential::Sequential/ResidualPRelu[conv_4_relu]/Conv2d[negative]/input.67
        self.module_33 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_4_relu]/ReLU[relu]/input.69
        self.module_34 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=128, bias=False) #Sequential::Sequential/ResidualPRelu[conv_4_relu]/Conv2d[slope]/6261
        self.module_35 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_4_relu]/input.71
        self.module_36 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[3, 3], stride=[2, 2], padding=[1, 1], dilation=[1, 1], groups=128, bias=True) #Sequential::Sequential/Conv2d[conv_5_dw_conv2d]/input.73
        self.module_37 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=128, bias=False) #Sequential::Sequential/ResidualPRelu[conv_5_dw_relu]/Conv2d[negative]/input.77
        self.module_38 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_5_dw_relu]/ReLU[relu]/input.79
        self.module_39 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=128, bias=False) #Sequential::Sequential/ResidualPRelu[conv_5_dw_relu]/Conv2d[slope]/6329
        self.module_40 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_5_dw_relu]/input.81
        self.module_41 = py_nndct.nn.Conv2d(in_channels=128, out_channels=256, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_5_conv2d]/input.83
        self.module_42 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=256, bias=False) #Sequential::Sequential/ResidualPRelu[conv_5_relu]/Conv2d[negative]/input.87
        self.module_43 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_5_relu]/ReLU[relu]/input.89
        self.module_44 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=256, bias=False) #Sequential::Sequential/ResidualPRelu[conv_5_relu]/Conv2d[slope]/6397
        self.module_45 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_5_relu]/input.91
        self.module_46 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=256, bias=True) #Sequential::Sequential/Conv2d[conv_6_dw_conv2d]/input.93
        self.module_47 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=256, bias=False) #Sequential::Sequential/ResidualPRelu[conv_6_dw_relu]/Conv2d[negative]/input.97
        self.module_48 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_6_dw_relu]/ReLU[relu]/input.99
        self.module_49 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=256, bias=False) #Sequential::Sequential/ResidualPRelu[conv_6_dw_relu]/Conv2d[slope]/6465
        self.module_50 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_6_dw_relu]/input.101
        self.module_51 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_6_conv2d]/input.103
        self.module_52 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=256, bias=False) #Sequential::Sequential/ResidualPRelu[conv_6_relu]/Conv2d[negative]/input.107
        self.module_53 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_6_relu]/ReLU[relu]/input.109
        self.module_54 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=256, bias=False) #Sequential::Sequential/ResidualPRelu[conv_6_relu]/Conv2d[slope]/6533
        self.module_55 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_6_relu]/input.111
        self.module_56 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[3, 3], stride=[2, 2], padding=[1, 1], dilation=[1, 1], groups=256, bias=True) #Sequential::Sequential/Conv2d[conv_7_dw_conv2d]/input.113
        self.module_57 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=256, bias=False) #Sequential::Sequential/ResidualPRelu[conv_7_dw_relu]/Conv2d[negative]/input.117
        self.module_58 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_7_dw_relu]/ReLU[relu]/input.119
        self.module_59 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=256, bias=False) #Sequential::Sequential/ResidualPRelu[conv_7_dw_relu]/Conv2d[slope]/6601
        self.module_60 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_7_dw_relu]/input.121
        self.module_61 = py_nndct.nn.Conv2d(in_channels=256, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_7_conv2d]/input.123
        self.module_62 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_7_relu]/Conv2d[negative]/input.127
        self.module_63 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_7_relu]/ReLU[relu]/input.129
        self.module_64 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_7_relu]/Conv2d[slope]/6669
        self.module_65 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_7_relu]/input.131
        self.module_66 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=512, bias=True) #Sequential::Sequential/Conv2d[conv_8_dw_conv2d]/input.133
        self.module_67 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_8_dw_relu]/Conv2d[negative]/input.137
        self.module_68 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_8_dw_relu]/ReLU[relu]/input.139
        self.module_69 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_8_dw_relu]/Conv2d[slope]/6737
        self.module_70 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_8_dw_relu]/input.141
        self.module_71 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_8_conv2d]/input.143
        self.module_72 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_8_relu]/Conv2d[negative]/input.147
        self.module_73 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_8_relu]/ReLU[relu]/input.149
        self.module_74 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_8_relu]/Conv2d[slope]/6805
        self.module_75 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_8_relu]/input.151
        self.module_76 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=512, bias=True) #Sequential::Sequential/Conv2d[conv_9_dw_conv2d]/input.153
        self.module_77 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_9_dw_relu]/Conv2d[negative]/input.157
        self.module_78 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_9_dw_relu]/ReLU[relu]/input.159
        self.module_79 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_9_dw_relu]/Conv2d[slope]/6873
        self.module_80 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_9_dw_relu]/input.161
        self.module_81 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_9_conv2d]/input.163
        self.module_82 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_9_relu]/Conv2d[negative]/input.167
        self.module_83 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_9_relu]/ReLU[relu]/input.169
        self.module_84 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_9_relu]/Conv2d[slope]/6941
        self.module_85 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_9_relu]/input.171
        self.module_86 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=512, bias=True) #Sequential::Sequential/Conv2d[conv_10_dw_conv2d]/input.173
        self.module_87 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_10_dw_relu]/Conv2d[negative]/input.177
        self.module_88 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_10_dw_relu]/ReLU[relu]/input.179
        self.module_89 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_10_dw_relu]/Conv2d[slope]/7009
        self.module_90 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_10_dw_relu]/input.181
        self.module_91 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_10_conv2d]/input.183
        self.module_92 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_10_relu]/Conv2d[negative]/input.187
        self.module_93 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_10_relu]/ReLU[relu]/input.189
        self.module_94 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_10_relu]/Conv2d[slope]/7077
        self.module_95 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_10_relu]/input.191
        self.module_96 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=512, bias=True) #Sequential::Sequential/Conv2d[conv_11_dw_conv2d]/input.193
        self.module_97 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_11_dw_relu]/Conv2d[negative]/input.197
        self.module_98 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_11_dw_relu]/ReLU[relu]/input.199
        self.module_99 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_11_dw_relu]/Conv2d[slope]/7145
        self.module_100 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_11_dw_relu]/input.201
        self.module_101 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_11_conv2d]/input.203
        self.module_102 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_11_relu]/Conv2d[negative]/input.207
        self.module_103 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_11_relu]/ReLU[relu]/input.209
        self.module_104 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_11_relu]/Conv2d[slope]/7213
        self.module_105 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_11_relu]/input.211
        self.module_106 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=512, bias=True) #Sequential::Sequential/Conv2d[conv_12_dw_conv2d]/input.213
        self.module_107 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_12_dw_relu]/Conv2d[negative]/input.217
        self.module_108 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_12_dw_relu]/ReLU[relu]/input.219
        self.module_109 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_12_dw_relu]/Conv2d[slope]/7281
        self.module_110 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_12_dw_relu]/input.221
        self.module_111 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_12_conv2d]/input.223
        self.module_112 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_12_relu]/Conv2d[negative]/input.227
        self.module_113 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_12_relu]/ReLU[relu]/input.229
        self.module_114 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_12_relu]/Conv2d[slope]/7349
        self.module_115 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_12_relu]/input.231
        self.module_116 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[3, 3], stride=[2, 2], padding=[1, 1], dilation=[1, 1], groups=512, bias=True) #Sequential::Sequential/Conv2d[conv_13_dw_conv2d]/input.233
        self.module_117 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_13_dw_relu]/Conv2d[negative]/input.237
        self.module_118 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_13_dw_relu]/ReLU[relu]/input.239
        self.module_119 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=512, bias=False) #Sequential::Sequential/ResidualPRelu[conv_13_dw_relu]/Conv2d[slope]/7417
        self.module_120 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_13_dw_relu]/input.241
        self.module_121 = py_nndct.nn.Conv2d(in_channels=512, out_channels=1024, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_13_conv2d]/input.243
        self.module_122 = py_nndct.nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1024, bias=False) #Sequential::Sequential/ResidualPRelu[conv_13_relu]/Conv2d[negative]/input.247
        self.module_123 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_13_relu]/ReLU[relu]/input.249
        self.module_124 = py_nndct.nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1024, bias=False) #Sequential::Sequential/ResidualPRelu[conv_13_relu]/Conv2d[slope]/7485
        self.module_125 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_13_relu]/input.251
        self.module_126 = py_nndct.nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=1024, bias=True) #Sequential::Sequential/Conv2d[conv_14_dw_conv2d]/input.253
        self.module_127 = py_nndct.nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1024, bias=False) #Sequential::Sequential/ResidualPRelu[conv_14_dw_relu]/Conv2d[negative]/input.257
        self.module_128 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_14_dw_relu]/ReLU[relu]/input.259
        self.module_129 = py_nndct.nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1024, bias=False) #Sequential::Sequential/ResidualPRelu[conv_14_dw_relu]/Conv2d[slope]/7553
        self.module_130 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_14_dw_relu]/input.261
        self.module_131 = py_nndct.nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_14_conv2d]/input.263
        self.module_132 = py_nndct.nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1024, bias=False) #Sequential::Sequential/ResidualPRelu[conv_14_relu]/Conv2d[negative]/input.267
        self.module_133 = py_nndct.nn.ReLU(inplace=False) #Sequential::Sequential/ResidualPRelu[conv_14_relu]/ReLU[relu]/input.269
        self.module_134 = py_nndct.nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1024, bias=False) #Sequential::Sequential/ResidualPRelu[conv_14_relu]/Conv2d[slope]/7621
        self.module_135 = py_nndct.nn.Add() #Sequential::Sequential/ResidualPRelu[conv_14_relu]/input.271
        self.module_136 = py_nndct.nn.BatchNorm(num_features=1024, eps=0.0, momentum=0.1) #Sequential::Sequential/BatchNorm2d[bn1]/input.273
        self.module_137 = py_nndct.nn.Conv2d(in_channels=1024, out_channels=256, kernel_size=[7, 7], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=2, bias=True) #Sequential::Sequential/GroupedSpatialFullyConnected[pre_fc1]/Conv2d[partition]/input.277
        self.module_138 = py_nndct.nn.Conv2d(in_channels=256, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/GroupedSpatialFullyConnected[pre_fc1]/Conv2d[sum]/input
        self.module_139 = py_nndct.nn.Module('nndct_flatten') #Sequential::Sequential/Flatten[output_flatten]/7678

    @py_nndct.nn.forward_processor
    def forward(self, *args):
        output_module_0 = self.module_0(input=args[0])
        output_module_0 = self.module_1(output_module_0)
        output_module_2 = self.module_2(output_module_0)
        output_module_2 = self.module_3(output_module_2)
        output_module_2 = self.module_4(output_module_2)
        output_module_5 = self.module_5(input=output_module_0, other=output_module_2, alpha=1)
        output_module_5 = self.module_6(output_module_5)
        output_module_7 = self.module_7(output_module_5)
        output_module_7 = self.module_8(output_module_7)
        output_module_7 = self.module_9(output_module_7)
        output_module_10 = self.module_10(input=output_module_5, other=output_module_7, alpha=1)
        output_module_10 = self.module_11(output_module_10)
        output_module_12 = self.module_12(output_module_10)
        output_module_12 = self.module_13(output_module_12)
        output_module_12 = self.module_14(output_module_12)
        output_module_15 = self.module_15(input=output_module_10, other=output_module_12, alpha=1)
        output_module_15 = self.module_16(output_module_15)
        output_module_17 = self.module_17(output_module_15)
        output_module_17 = self.module_18(output_module_17)
        output_module_17 = self.module_19(output_module_17)
        output_module_20 = self.module_20(input=output_module_15, other=output_module_17, alpha=1)
        output_module_20 = self.module_21(output_module_20)
        output_module_22 = self.module_22(output_module_20)
        output_module_22 = self.module_23(output_module_22)
        output_module_22 = self.module_24(output_module_22)
        output_module_25 = self.module_25(input=output_module_20, other=output_module_22, alpha=1)
        output_module_25 = self.module_26(output_module_25)
        output_module_27 = self.module_27(output_module_25)
        output_module_27 = self.module_28(output_module_27)
        output_module_27 = self.module_29(output_module_27)
        output_module_30 = self.module_30(input=output_module_25, other=output_module_27, alpha=1)
        output_module_30 = self.module_31(output_module_30)
        output_module_32 = self.module_32(output_module_30)
        output_module_32 = self.module_33(output_module_32)
        output_module_32 = self.module_34(output_module_32)
        output_module_35 = self.module_35(input=output_module_30, other=output_module_32, alpha=1)
        output_module_35 = self.module_36(output_module_35)
        output_module_37 = self.module_37(output_module_35)
        output_module_37 = self.module_38(output_module_37)
        output_module_37 = self.module_39(output_module_37)
        output_module_40 = self.module_40(input=output_module_35, other=output_module_37, alpha=1)
        output_module_40 = self.module_41(output_module_40)
        output_module_42 = self.module_42(output_module_40)
        output_module_42 = self.module_43(output_module_42)
        output_module_42 = self.module_44(output_module_42)
        output_module_45 = self.module_45(input=output_module_40, other=output_module_42, alpha=1)
        output_module_45 = self.module_46(output_module_45)
        output_module_47 = self.module_47(output_module_45)
        output_module_47 = self.module_48(output_module_47)
        output_module_47 = self.module_49(output_module_47)
        output_module_50 = self.module_50(input=output_module_45, other=output_module_47, alpha=1)
        output_module_50 = self.module_51(output_module_50)
        output_module_52 = self.module_52(output_module_50)
        output_module_52 = self.module_53(output_module_52)
        output_module_52 = self.module_54(output_module_52)
        output_module_55 = self.module_55(input=output_module_50, other=output_module_52, alpha=1)
        output_module_55 = self.module_56(output_module_55)
        output_module_57 = self.module_57(output_module_55)
        output_module_57 = self.module_58(output_module_57)
        output_module_57 = self.module_59(output_module_57)
        output_module_60 = self.module_60(input=output_module_55, other=output_module_57, alpha=1)
        output_module_60 = self.module_61(output_module_60)
        output_module_62 = self.module_62(output_module_60)
        output_module_62 = self.module_63(output_module_62)
        output_module_62 = self.module_64(output_module_62)
        output_module_65 = self.module_65(input=output_module_60, other=output_module_62, alpha=1)
        output_module_65 = self.module_66(output_module_65)
        output_module_67 = self.module_67(output_module_65)
        output_module_67 = self.module_68(output_module_67)
        output_module_67 = self.module_69(output_module_67)
        output_module_70 = self.module_70(input=output_module_65, other=output_module_67, alpha=1)
        output_module_70 = self.module_71(output_module_70)
        output_module_72 = self.module_72(output_module_70)
        output_module_72 = self.module_73(output_module_72)
        output_module_72 = self.module_74(output_module_72)
        output_module_75 = self.module_75(input=output_module_70, other=output_module_72, alpha=1)
        output_module_75 = self.module_76(output_module_75)
        output_module_77 = self.module_77(output_module_75)
        output_module_77 = self.module_78(output_module_77)
        output_module_77 = self.module_79(output_module_77)
        output_module_80 = self.module_80(input=output_module_75, other=output_module_77, alpha=1)
        output_module_80 = self.module_81(output_module_80)
        output_module_82 = self.module_82(output_module_80)
        output_module_82 = self.module_83(output_module_82)
        output_module_82 = self.module_84(output_module_82)
        output_module_85 = self.module_85(input=output_module_80, other=output_module_82, alpha=1)
        output_module_85 = self.module_86(output_module_85)
        output_module_87 = self.module_87(output_module_85)
        output_module_87 = self.module_88(output_module_87)
        output_module_87 = self.module_89(output_module_87)
        output_module_90 = self.module_90(input=output_module_85, other=output_module_87, alpha=1)
        output_module_90 = self.module_91(output_module_90)
        output_module_92 = self.module_92(output_module_90)
        output_module_92 = self.module_93(output_module_92)
        output_module_92 = self.module_94(output_module_92)
        output_module_95 = self.module_95(input=output_module_90, other=output_module_92, alpha=1)
        output_module_95 = self.module_96(output_module_95)
        output_module_97 = self.module_97(output_module_95)
        output_module_97 = self.module_98(output_module_97)
        output_module_97 = self.module_99(output_module_97)
        output_module_100 = self.module_100(input=output_module_95, other=output_module_97, alpha=1)
        output_module_100 = self.module_101(output_module_100)
        output_module_102 = self.module_102(output_module_100)
        output_module_102 = self.module_103(output_module_102)
        output_module_102 = self.module_104(output_module_102)
        output_module_105 = self.module_105(input=output_module_100, other=output_module_102, alpha=1)
        output_module_105 = self.module_106(output_module_105)
        output_module_107 = self.module_107(output_module_105)
        output_module_107 = self.module_108(output_module_107)
        output_module_107 = self.module_109(output_module_107)
        output_module_110 = self.module_110(input=output_module_105, other=output_module_107, alpha=1)
        output_module_110 = self.module_111(output_module_110)
        output_module_112 = self.module_112(output_module_110)
        output_module_112 = self.module_113(output_module_112)
        output_module_112 = self.module_114(output_module_112)
        output_module_115 = self.module_115(input=output_module_110, other=output_module_112, alpha=1)
        output_module_115 = self.module_116(output_module_115)
        output_module_117 = self.module_117(output_module_115)
        output_module_117 = self.module_118(output_module_117)
        output_module_117 = self.module_119(output_module_117)
        output_module_120 = self.module_120(input=output_module_115, other=output_module_117, alpha=1)
        output_module_120 = self.module_121(output_module_120)
        output_module_122 = self.module_122(output_module_120)
        output_module_122 = self.module_123(output_module_122)
        output_module_122 = self.module_124(output_module_122)
        output_module_125 = self.module_125(input=output_module_120, other=output_module_122, alpha=1)
        output_module_125 = self.module_126(output_module_125)
        output_module_127 = self.module_127(output_module_125)
        output_module_127 = self.module_128(output_module_127)
        output_module_127 = self.module_129(output_module_127)
        output_module_130 = self.module_130(input=output_module_125, other=output_module_127, alpha=1)
        output_module_130 = self.module_131(output_module_130)
        output_module_132 = self.module_132(output_module_130)
        output_module_132 = self.module_133(output_module_132)
        output_module_132 = self.module_134(output_module_132)
        output_module_135 = self.module_135(input=output_module_130, other=output_module_132, alpha=1)
        output_module_135 = self.module_136(output_module_135)
        output_module_135 = self.module_137(output_module_135)
        output_module_135 = self.module_138(output_module_135)
        output_module_135 = self.module_139(input=output_module_135, start_dim=1, end_dim=-1)
        return output_module_135
