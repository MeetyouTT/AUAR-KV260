# GENETARED BY NNDCT, DO NOT EDIT!

import torch
from torch import tensor
import pytorch_nndct as py_nndct

class YuNetCore(py_nndct.nn.NndctQuantModel):
    def __init__(self):
        super(YuNetCore, self).__init__()
        self.module_0 = py_nndct.nn.Input() #YuNetCore::input_0
        self.module_1 = py_nndct.nn.Conv2d(in_channels=3, out_channels=16, kernel_size=[3, 3], stride=[2, 2], padding=[1, 1], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[0]/input.3
        self.module_2 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[1]/input.5
        self.module_3 = py_nndct.nn.Conv2d(in_channels=16, out_channels=16, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[2]/input.7
        self.module_4 = py_nndct.nn.Conv2d(in_channels=16, out_channels=16, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=16, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[3]/input.9
        self.module_5 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[4]/2206
        self.module_6 = py_nndct.nn.MaxPool2d(kernel_size=[2, 2], stride=[2, 2], padding=[0, 0], dilation=[1, 1], ceil_mode=False) #YuNetCore::YuNetCore/MaxPool2d[layers]/ModuleList[5]/input.11
        self.module_7 = py_nndct.nn.Conv2d(in_channels=16, out_channels=16, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[6]/input.13
        self.module_8 = py_nndct.nn.Conv2d(in_channels=16, out_channels=16, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=16, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[7]/input.15
        self.module_9 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[8]/input.17
        self.module_10 = py_nndct.nn.Conv2d(in_channels=16, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[9]/input.19
        self.module_11 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[10]/input.21
        self.module_12 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[11]/input.23
        self.module_13 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[12]/input.25
        self.module_14 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[13]/input.27
        self.module_15 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[14]/input.29
        self.module_16 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[15]/input.31
        self.module_17 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[16]/input.33
        self.module_18 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[17]/2376
        self.module_19 = py_nndct.nn.MaxPool2d(kernel_size=[2, 2], stride=[2, 2], padding=[0, 0], dilation=[1, 1], ceil_mode=False) #YuNetCore::YuNetCore/MaxPool2d[layers]/ModuleList[18]/input.35
        self.module_20 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[19]/input.37
        self.module_21 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[20]/input.39
        self.module_22 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[21]/input.41
        self.module_23 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[22]/input.43
        self.module_24 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[23]/input.45
        self.module_25 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[24]/input.83
        self.module_26 = py_nndct.nn.MaxPool2d(kernel_size=[2, 2], stride=[2, 2], padding=[0, 0], dilation=[1, 1], ceil_mode=False) #YuNetCore::YuNetCore/MaxPool2d[layers]/ModuleList[25]/input.47
        self.module_27 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[26]/input.49
        self.module_28 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[27]/input.51
        self.module_29 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[28]/input.53
        self.module_30 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[29]/input.55
        self.module_31 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[30]/input.57
        self.module_32 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[31]/input.93
        self.module_33 = py_nndct.nn.MaxPool2d(kernel_size=[2, 2], stride=[2, 2], padding=[0, 0], dilation=[1, 1], ceil_mode=False) #YuNetCore::YuNetCore/MaxPool2d[layers]/ModuleList[32]/input.59
        self.module_34 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[33]/input.61
        self.module_35 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[34]/input.63
        self.module_36 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[35]/input.65
        self.module_37 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[36]/input.67
        self.module_38 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[37]/input.69
        self.module_39 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[38]/input.103
        self.module_40 = py_nndct.nn.MaxPool2d(kernel_size=[2, 2], stride=[2, 2], padding=[0, 0], dilation=[1, 1], ceil_mode=False) #YuNetCore::YuNetCore/MaxPool2d[layers]/ModuleList[39]/input.71
        self.module_41 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[40]/input.73
        self.module_42 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[41]/input.75
        self.module_43 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[42]/input.77
        self.module_44 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[43]/input.79
        self.module_45 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[44]/input.81
        self.module_46 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[45]/input.113
        self.module_47 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[46]/input.85
        self.module_48 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[47]/input.87
        self.module_49 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[48]/input.89
        self.module_50 = py_nndct.nn.Conv2d(in_channels=64, out_channels=51, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[49]/input.91
        self.module_51 = py_nndct.nn.Conv2d(in_channels=51, out_channels=51, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=51, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[50]/2821
        self.module_52 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[51]/input.95
        self.module_53 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[52]/input.97
        self.module_54 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[53]/input.99
        self.module_55 = py_nndct.nn.Conv2d(in_channels=64, out_channels=34, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[54]/input.101
        self.module_56 = py_nndct.nn.Conv2d(in_channels=34, out_channels=34, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=34, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[55]/2898
        self.module_57 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[56]/input.105
        self.module_58 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[57]/input.107
        self.module_59 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[58]/input.109
        self.module_60 = py_nndct.nn.Conv2d(in_channels=64, out_channels=34, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[59]/input.111
        self.module_61 = py_nndct.nn.Conv2d(in_channels=34, out_channels=34, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=34, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[60]/2975
        self.module_62 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[61]/input.115
        self.module_63 = py_nndct.nn.Conv2d(in_channels=64, out_channels=64, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=64, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[62]/input.117
        self.module_64 = py_nndct.nn.ReLU(inplace=False) #YuNetCore::YuNetCore/ReLU[layers]/ModuleList[63]/input.119
        self.module_65 = py_nndct.nn.Conv2d(in_channels=64, out_channels=51, kernel_size=[1, 1], stride=[1, 1], padding=[0, 0], dilation=[1, 1], groups=1, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[64]/input
        self.module_66 = py_nndct.nn.Conv2d(in_channels=51, out_channels=51, kernel_size=[3, 3], stride=[1, 1], padding=[1, 1], dilation=[1, 1], groups=51, bias=True) #YuNetCore::YuNetCore/Conv2d[layers]/ModuleList[65]/3052

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
        output_module_26 = self.module_26(output_module_0)
        output_module_26 = self.module_27(output_module_26)
        output_module_26 = self.module_28(output_module_26)
        output_module_26 = self.module_29(output_module_26)
        output_module_26 = self.module_30(output_module_26)
        output_module_26 = self.module_31(output_module_26)
        output_module_26 = self.module_32(output_module_26)
        output_module_33 = self.module_33(output_module_26)
        output_module_33 = self.module_34(output_module_33)
        output_module_33 = self.module_35(output_module_33)
        output_module_33 = self.module_36(output_module_33)
        output_module_33 = self.module_37(output_module_33)
        output_module_33 = self.module_38(output_module_33)
        output_module_33 = self.module_39(output_module_33)
        output_module_40 = self.module_40(output_module_33)
        output_module_40 = self.module_41(output_module_40)
        output_module_40 = self.module_42(output_module_40)
        output_module_40 = self.module_43(output_module_40)
        output_module_40 = self.module_44(output_module_40)
        output_module_40 = self.module_45(output_module_40)
        output_module_40 = self.module_46(output_module_40)
        output_module_47 = self.module_47(output_module_0)
        output_module_47 = self.module_48(output_module_47)
        output_module_47 = self.module_49(output_module_47)
        output_module_47 = self.module_50(output_module_47)
        output_module_47 = self.module_51(output_module_47)
        output_module_52 = self.module_52(output_module_26)
        output_module_52 = self.module_53(output_module_52)
        output_module_52 = self.module_54(output_module_52)
        output_module_52 = self.module_55(output_module_52)
        output_module_52 = self.module_56(output_module_52)
        output_module_57 = self.module_57(output_module_33)
        output_module_57 = self.module_58(output_module_57)
        output_module_57 = self.module_59(output_module_57)
        output_module_57 = self.module_60(output_module_57)
        output_module_57 = self.module_61(output_module_57)
        output_module_40 = self.module_62(output_module_40)
        output_module_40 = self.module_63(output_module_40)
        output_module_40 = self.module_64(output_module_40)
        output_module_40 = self.module_65(output_module_40)
        output_module_40 = self.module_66(output_module_40)
        return (output_module_47,output_module_52,output_module_57,output_module_40)
