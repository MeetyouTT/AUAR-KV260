# GENETARED BY NNDCT, DO NOT EDIT!

import torch
from torch import tensor
import pytorch_nndct as py_nndct

class Sequential(py_nndct.nn.NndctQuantModel):
    def __init__(self):
        super(Sequential, self).__init__()
        self.module_0 = py_nndct.nn.Input() #Sequential::input_0
        self.module_1 = py_nndct.nn.Conv2d(in_channels=3, out_channels=32, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_1_conv2d]/input.3
        self.module_2 = py_nndct.nn.PReLU(num_parameters=32, init=0.25) #Sequential::Sequential/PReLU[conv_1_relu]/input.5
        self.module_3 = py_nndct.nn.Conv2d(in_channels=32, out_channels=32, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=32, bias=True) #Sequential::Sequential/Conv2d[conv_2_dw_conv2d]/input.7
        self.module_4 = py_nndct.nn.PReLU(num_parameters=32, init=0.25) #Sequential::Sequential/PReLU[conv_2_dw_relu]/input.9
        self.module_5 = py_nndct.nn.Conv2d(in_channels=32, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_2_conv2d]/input.11
        self.module_6 = py_nndct.nn.PReLU(num_parameters=64, init=0.25) #Sequential::Sequential/PReLU[conv_2_relu]/input.13
        self.module_7 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[2, 2], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #Sequential::Sequential/Conv2d[conv_3_dw_conv2d]/input.15
        self.module_8 = py_nndct.nn.PReLU(num_parameters=64, init=0.25) #Sequential::Sequential/PReLU[conv_3_dw_relu]/input.17
        self.module_9 = py_nndct.nn.Conv2d(in_channels=64, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_3_conv2d]/input.19
        self.module_10 = py_nndct.nn.PReLU(num_parameters=128, init=0.25) #Sequential::Sequential/PReLU[conv_3_relu]/input.21
        self.module_11 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=128, bias=True) #Sequential::Sequential/Conv2d[conv_4_dw_conv2d]/input.23
        self.module_12 = py_nndct.nn.PReLU(num_parameters=128, init=0.25) #Sequential::Sequential/PReLU[conv_4_dw_relu]/input.25
        self.module_13 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_4_conv2d]/input.27
        self.module_14 = py_nndct.nn.PReLU(num_parameters=128, init=0.25) #Sequential::Sequential/PReLU[conv_4_relu]/input.29
        self.module_15 = py_nndct.nn.Conv2d(in_channels=128, out_channels=128, kernel_size=[3, 3], stride=[2, 2], padding=[1, 1], dilation=[1, 1], groups=128, bias=True) #Sequential::Sequential/Conv2d[conv_5_dw_conv2d]/input.31
        self.module_16 = py_nndct.nn.PReLU(num_parameters=128, init=0.25) #Sequential::Sequential/PReLU[conv_5_dw_relu]/input.33
        self.module_17 = py_nndct.nn.Conv2d(in_channels=128, out_channels=256, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_5_conv2d]/input.35
        self.module_18 = py_nndct.nn.PReLU(num_parameters=256, init=0.25) #Sequential::Sequential/PReLU[conv_5_relu]/input.37
        self.module_19 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=256, bias=True) #Sequential::Sequential/Conv2d[conv_6_dw_conv2d]/input.39
        self.module_20 = py_nndct.nn.PReLU(num_parameters=256, init=0.25) #Sequential::Sequential/PReLU[conv_6_dw_relu]/input.41
        self.module_21 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_6_conv2d]/input.43
        self.module_22 = py_nndct.nn.PReLU(num_parameters=256, init=0.25) #Sequential::Sequential/PReLU[conv_6_relu]/input.45
        self.module_23 = py_nndct.nn.Conv2d(in_channels=256, out_channels=256, kernel_size=[3, 3], stride=[2, 2], padding=[1, 1], dilation=[1, 1], groups=256, bias=True) #Sequential::Sequential/Conv2d[conv_7_dw_conv2d]/input.47
        self.module_24 = py_nndct.nn.PReLU(num_parameters=256, init=0.25) #Sequential::Sequential/PReLU[conv_7_dw_relu]/input.49
        self.module_25 = py_nndct.nn.Conv2d(in_channels=256, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_7_conv2d]/input.51
        self.module_26 = py_nndct.nn.PReLU(num_parameters=512, init=0.25) #Sequential::Sequential/PReLU[conv_7_relu]/input.53
        self.module_27 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=512, bias=True) #Sequential::Sequential/Conv2d[conv_8_dw_conv2d]/input.55
        self.module_28 = py_nndct.nn.PReLU(num_parameters=512, init=0.25) #Sequential::Sequential/PReLU[conv_8_dw_relu]/input.57
        self.module_29 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_8_conv2d]/input.59
        self.module_30 = py_nndct.nn.PReLU(num_parameters=512, init=0.25) #Sequential::Sequential/PReLU[conv_8_relu]/input.61
        self.module_31 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=512, bias=True) #Sequential::Sequential/Conv2d[conv_9_dw_conv2d]/input.63
        self.module_32 = py_nndct.nn.PReLU(num_parameters=512, init=0.25) #Sequential::Sequential/PReLU[conv_9_dw_relu]/input.65
        self.module_33 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_9_conv2d]/input.67
        self.module_34 = py_nndct.nn.PReLU(num_parameters=512, init=0.25) #Sequential::Sequential/PReLU[conv_9_relu]/input.69
        self.module_35 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=512, bias=True) #Sequential::Sequential/Conv2d[conv_10_dw_conv2d]/input.71
        self.module_36 = py_nndct.nn.PReLU(num_parameters=512, init=0.25) #Sequential::Sequential/PReLU[conv_10_dw_relu]/input.73
        self.module_37 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_10_conv2d]/input.75
        self.module_38 = py_nndct.nn.PReLU(num_parameters=512, init=0.25) #Sequential::Sequential/PReLU[conv_10_relu]/input.77
        self.module_39 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=512, bias=True) #Sequential::Sequential/Conv2d[conv_11_dw_conv2d]/input.79
        self.module_40 = py_nndct.nn.PReLU(num_parameters=512, init=0.25) #Sequential::Sequential/PReLU[conv_11_dw_relu]/input.81
        self.module_41 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_11_conv2d]/input.83
        self.module_42 = py_nndct.nn.PReLU(num_parameters=512, init=0.25) #Sequential::Sequential/PReLU[conv_11_relu]/input.85
        self.module_43 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=512, bias=True) #Sequential::Sequential/Conv2d[conv_12_dw_conv2d]/input.87
        self.module_44 = py_nndct.nn.PReLU(num_parameters=512, init=0.25) #Sequential::Sequential/PReLU[conv_12_dw_relu]/input.89
        self.module_45 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_12_conv2d]/input.91
        self.module_46 = py_nndct.nn.PReLU(num_parameters=512, init=0.25) #Sequential::Sequential/PReLU[conv_12_relu]/input.93
        self.module_47 = py_nndct.nn.Conv2d(in_channels=512, out_channels=512, kernel_size=[3, 3], stride=[2, 2], padding=[1, 1], dilation=[1, 1], groups=512, bias=True) #Sequential::Sequential/Conv2d[conv_13_dw_conv2d]/input.95
        self.module_48 = py_nndct.nn.PReLU(num_parameters=512, init=0.25) #Sequential::Sequential/PReLU[conv_13_dw_relu]/input.97
        self.module_49 = py_nndct.nn.Conv2d(in_channels=512, out_channels=1024, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_13_conv2d]/input.99
        self.module_50 = py_nndct.nn.PReLU(num_parameters=1024, init=0.25) #Sequential::Sequential/PReLU[conv_13_relu]/input.101
        self.module_51 = py_nndct.nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=1024, bias=True) #Sequential::Sequential/Conv2d[conv_14_dw_conv2d]/input.103
        self.module_52 = py_nndct.nn.PReLU(num_parameters=1024, init=0.25) #Sequential::Sequential/PReLU[conv_14_dw_relu]/input.105
        self.module_53 = py_nndct.nn.Conv2d(in_channels=1024, out_channels=1024, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #Sequential::Sequential/Conv2d[conv_14_conv2d]/input.107
        self.module_54 = py_nndct.nn.PReLU(num_parameters=1024, init=0.25) #Sequential::Sequential/PReLU[conv_14_relu]/input.109
        self.module_55 = py_nndct.nn.BatchNorm(num_features=1024, eps=0.0, momentum=0.1) #Sequential::Sequential/BatchNorm2d[bn1]/input.111
        self.module_56 = py_nndct.nn.Module('nndct_flatten') #Sequential::Sequential/Flatten[flatten_254]/2843
        self.module_57 = py_nndct.nn.Linear(in_features=50176, out_features=128, bias=True) #Sequential::Sequential/Linear[pre_fc1]/input
        self.module_58 = py_nndct.nn.BatchNorm(num_features=128, eps=0.0, momentum=0.1) #Sequential::Sequential/BatchNorm1d[fc1]/2849

    @py_nndct.nn.forward_processor
    def forward(self, *args):
        output_module_0 = self.module_0(input=args[0])
        output_module_0 = self.module_1(output_module_0)
        output_module_0 = self.module_2(output_module_0)
        output_module_0 = self.module_3(output_module_0)
        output_module_0 = self.module_4(output_module_0)
        output_module_0 = self.module_5(output_module_0)
        output_module_0 = self.module_6(output_module_0)
        output_module_0 = self.module_7(output_module_0)
        output_module_0 = self.module_8(output_module_0)
        output_module_0 = self.module_9(output_module_0)
        output_module_0 = self.module_10(output_module_0)
        output_module_0 = self.module_11(output_module_0)
        output_module_0 = self.module_12(output_module_0)
        output_module_0 = self.module_13(output_module_0)
        output_module_0 = self.module_14(output_module_0)
        output_module_0 = self.module_15(output_module_0)
        output_module_0 = self.module_16(output_module_0)
        output_module_0 = self.module_17(output_module_0)
        output_module_0 = self.module_18(output_module_0)
        output_module_0 = self.module_19(output_module_0)
        output_module_0 = self.module_20(output_module_0)
        output_module_0 = self.module_21(output_module_0)
        output_module_0 = self.module_22(output_module_0)
        output_module_0 = self.module_23(output_module_0)
        output_module_0 = self.module_24(output_module_0)
        output_module_0 = self.module_25(output_module_0)
        output_module_0 = self.module_26(output_module_0)
        output_module_0 = self.module_27(output_module_0)
        output_module_0 = self.module_28(output_module_0)
        output_module_0 = self.module_29(output_module_0)
        output_module_0 = self.module_30(output_module_0)
        output_module_0 = self.module_31(output_module_0)
        output_module_0 = self.module_32(output_module_0)
        output_module_0 = self.module_33(output_module_0)
        output_module_0 = self.module_34(output_module_0)
        output_module_0 = self.module_35(output_module_0)
        output_module_0 = self.module_36(output_module_0)
        output_module_0 = self.module_37(output_module_0)
        output_module_0 = self.module_38(output_module_0)
        output_module_0 = self.module_39(output_module_0)
        output_module_0 = self.module_40(output_module_0)
        output_module_0 = self.module_41(output_module_0)
        output_module_0 = self.module_42(output_module_0)
        output_module_0 = self.module_43(output_module_0)
        output_module_0 = self.module_44(output_module_0)
        output_module_0 = self.module_45(output_module_0)
        output_module_0 = self.module_46(output_module_0)
        output_module_0 = self.module_47(output_module_0)
        output_module_0 = self.module_48(output_module_0)
        output_module_0 = self.module_49(output_module_0)
        output_module_0 = self.module_50(output_module_0)
        output_module_0 = self.module_51(output_module_0)
        output_module_0 = self.module_52(output_module_0)
        output_module_0 = self.module_53(output_module_0)
        output_module_0 = self.module_54(output_module_0)
        output_module_0 = self.module_55(output_module_0)
        output_module_0 = self.module_56(input=output_module_0, start_dim=1, end_dim=-1)
        output_module_0 = self.module_57(output_module_0)
        output_module_0 = self.module_58(output_module_0)
        return output_module_0
