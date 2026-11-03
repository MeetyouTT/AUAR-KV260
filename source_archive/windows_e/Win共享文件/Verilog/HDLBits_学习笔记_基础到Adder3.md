# HDLBits Verilog 学习笔记：基础到 Adder3

这份笔记按 HDLBits 的学习顺序整理，范围从最基本的模块和逻辑门，到 Mux256to1v、半加器、全加器以及 Adder3。内容也专门解释了前面代码中出现的 always、for、向量位选和模块例化。

参考题目：

- [Mux256to1v：256 路、4 位宽多路选择器](https://hdlbits.01xz.net/wiki/Mux256to1v)
- [Adder3：3 位串行进位加法器](https://hdlbits.01xz.net/wiki/Adder3)

---

## 一、HDL 和 Verilog 是什么

HDL 是硬件描述语言（Hardware Description Language）。Verilog 描述的不是普通软件中的执行步骤，而是电路的结构和信号之间的关系。

例如：

~~~verilog
assign out = a & b;
~~~

表示建立一个 AND 门。只要 a 或 b 发生变化，out 就会根据 AND 逻辑变化。

Verilog 设计最重要的两个思维方式是：

1. **组合逻辑**：输出只由当前输入决定，没有记忆功能。
2. **时序逻辑**：输出还与时钟和之前保存的状态有关。

Mux256to1v、半加器、全加器和 Adder3 都属于组合逻辑。

---

## 二、模块的基本结构

~~~verilog
module top_module(
    input  a,
    input  b,
    output out
);

    assign out = a & b;

endmodule
~~~

### 2.1 关键字

| 关键字 | 含义 |
|---|---|
| module | 开始定义一个模块 |
| endmodule | 结束模块定义 |
| input | 输入端口，只能被模块读取 |
| output | 输出端口 |
| wire | 网络型信号，常用于 assign 和模块连接 |
| reg | Verilog 过程变量，可在 always 中赋值 |
| integer | 整数变量，常用于循环计数 |

HDLBits 通常要求顶层模块名为 top_module。模块端口声明中的逗号、括号和分号必须完整。

### 2.2 输入不能被赋值

下面的写法错误：

~~~verilog
sel = sel_out;
~~~

因为 sel 是 input，是外部输入信号。正确的方向应该是读取它：

~~~verilog
if (sel == i)
    out = data[i];
~~~

### 2.3 端口的默认类型

在传统 Verilog 中：

~~~verilog
output out;
~~~

默认相当于一个 wire。

如果输出在 always 块中赋值，应写成：

~~~verilog
output reg out;
~~~

连续赋值和过程赋值不能混用到同一个信号上。

---

## 三、常量、位宽和数字写法

~~~verilog
1'b0       // 1 位二进制 0
1'b1       // 1 位二进制 1
4'b1010    // 4 位二进制
8'd25      // 8 位十进制
8'hA5      // 8 位十六进制
~~~

基本格式是：

~~~text
位宽 ' 进制 数值
~~~

常见进制：

- b：二进制
- d：十进制
- h：十六进制
- o：八进制

例如：

~~~verilog
4'b1111 = 4'hF = 4'd15
~~~

指定位宽很重要。位宽太小会截断，位宽太大可能产生扩展位。

---

## 四、基本逻辑运算符

### 4.1 按位运算符

| 运算符 | 功能 | 示例 |
|---|---|---|
| ~ | 按位取反 | ~a |
| & | 按位 AND | a & b |
| \| | 按位 OR | a \| b |
| ^ | 按位 XOR | a ^ b |
| ~^ 或 ^~ | 按位 XNOR | a ~^ b |

示例：

~~~verilog
assign out_and  = a & b;
assign out_or   = a | b;
assign out_xor  = a ^ b;
assign out_nor  = ~(a | b);
assign out_nand = ~(a & b);
assign out_xnor = ~(a ^ b);
~~~

如果 a 和 b 是向量，按位运算会对每一位分别运算：

~~~text
4'b1010 & 4'b1100 = 4'b1000
~~~

### 4.2 逻辑运算符

~~~verilog
!a       // 逻辑 NOT
a && b   // 逻辑 AND
a || b   // 逻辑 OR
~~~

逻辑运算通常把操作数看成真假值；按位运算则逐位处理。处理向量时，必须确认自己需要的是哪一种。

### 4.3 比较运算符

~~~verilog
a == b
a != b
a < b
a > b
a <= b
a >= b
~~~

在多路选择器循环中经常使用：

~~~verilog
if (sel == i)
~~~

### 4.4 运算优先级

复杂表达式建议主动加括号：

~~~verilog
assign cout = (a & b) | (a & cin) | (b & cin);
~~~

不要依赖自己对优先级的记忆来省略括号。

---

## 五、向量、索引和切片

### 5.1 声明向量

~~~verilog
input  [7:0] data;
output [3:0] out;
~~~

[7:0] 表示 8 位信号，最高位是 data[7]，最低位是 data[0]。

### 5.2 选择单个位

~~~verilog
assign out = data[3];
~~~

### 5.3 选择连续位段

~~~verilog
assign out = data[7:4];
~~~

如果：

~~~verilog
data = 8'b10110011;
~~~

那么：

~~~text
data[7:4] = 4'b1011
data[3:0] = 4'b0011
~~~

### 5.4 位序

~~~text
[7:0]
~~~

通常表示从高位到低位的向量。data[0] 是最低位，不要把数组下标方向和数字书写方向混淆。

### 5.5 索引位选 +:

语法：

~~~verilog
vector[start +: width]
~~~

含义是从 start 开始，向高位选择固定的 width 位。

例如：

~~~verilog
in[0 +: 4]  // 等价于 in[3:0]
in[4 +: 4]  // 等价于 in[7:4]
in[8 +: 4]  // 等价于 in[11:8]
~~~

也有向低位选择的形式：

~~~verilog
vector[start -: width]
~~~

width 必须是固定常量，起始位置可以是变量。

### 5.6 拼接运算符

~~~verilog
assign out = {a, b};
~~~

如果 a 和 b 都是 2 位，{a,b} 就是 4 位。

可以重新排列位：

~~~verilog
assign out = {a[0], a[1], a[2], a[3]};
~~~

### 5.7 重复运算符

~~~verilog
assign out = {4{1'b1}};
~~~

结果是：

~~~verilog
4'b1111
~~~

嵌套示例：

~~~verilog
assign out = {2{2'b10}};
~~~

结果是：

~~~verilog
4'b1010
~~~

---

## 六、连续赋值 assign

~~~verilog
assign out = expression;
~~~

assign 描述的是持续存在的组合连接。例如：

~~~verilog
assign sum  = a ^ b ^ cin;
assign cout = (a & b) | (a & cin) | (b & cin);
~~~

assign 的特点：

- 输入改变时，输出自动重新计算
- 适合简单组合逻辑
- 输出通常声明为 wire
- 不需要 always
- 不需要 begin/end

---

## 七、组合逻辑 always @(*)

~~~verilog
module top_module(
    input      a,
    input      b,
    output reg out
);

    always @(*) begin
        out = a & b;
    end

endmodule
~~~

### 7.1 @(*) 的含义

@(*) 表示该过程块自动关注其中使用到的输入信号。任意相关输入变化时，块都会重新执行。

### 7.2 组合逻辑使用阻塞赋值

组合逻辑通常使用：

~~~verilog
=
~~~

例如：

~~~verilog
always @(*) begin
    out = a ^ b;
end
~~~

### 7.3 组合输出要覆盖所有路径

错误示例：

~~~verilog
always @(*) begin
    if (sel)
        out = a;
end
~~~

当 sel = 0 时，out 没有新值，综合器可能推导出锁存器。

推荐写法：

~~~verilog
always @(*) begin
    out = 4'b0000;

    if (sel)
        out = a;
end
~~~

### 7.4 if/else

~~~verilog
always @(*) begin
    if (sel == 1'b0)
        out = a;
    else
        out = b;
end
~~~

### 7.5 case

~~~verilog
always @(*) begin
    case (sel)
        2'b00: out = a;
        2'b01: out = b;
        2'b10: out = c;
        default: out = d;
    endcase
end
~~~

default 可以保证未匹配情况也有输出。

### 7.6 casez

casez 允许使用 z 或 ? 表示不关心位，适合优先编码器：

~~~verilog
always @(*) begin
    casez (in)
        4'b1???: out = 2'd3;
        4'b01??: out = 2'd2;
        4'b001?: out = 2'd1;
        4'b0001: out = 2'd0;
        default: out = 2'd0;
    endcase
end
~~~

casez 中排列顺序会影响优先级。

---

## 八、时序 always 的基础区别

虽然 Mux256to1v 和 Adder3 是组合逻辑，但 HDLBits 的前置内容也会接触时序过程块：

~~~verilog
always @(posedge clk) begin
    q <= d;
end
~~~

主要区别如下：

| 组合逻辑 | 时序逻辑 |
|---|---|
| always @(*) | always @(posedge clk) |
| 通常使用 = | 通常使用 <= |
| 输出只由当前输入决定 | 输出与时钟和过去状态有关 |
| 不保存状态 | 可以保存状态 |
| 常用于门、MUX、加法器 | 常用于触发器、寄存器、计数器 |

组合块使用阻塞赋值，时钟块使用非阻塞赋值，是 HDLBits 中很重要的编码习惯。

---

## 九、for 循环和整数变量

语法：

~~~verilog
integer i;

always @(*) begin
    for (i = 0; i < 8; i = i + 1) begin
        // 组合逻辑
    end
end
~~~

循环的三部分：

~~~text
初始化; 条件; 每次循环后的更新
~~~

例如：

~~~verilog
for (i = 0; i < 256; i = i + 1)
~~~

表示 i 从 0 变化到 255。

在可综合 Verilog 中，循环通常用于描述重复的硬件结构，而不是软件意义上的运行时循环。

你的多路选择器循环写法应为：

~~~verilog
integer i;

always @(*) begin
    out = 4'b0000;

    for (i = 0; i < 256; i = i + 1) begin
        if (sel == i)
            out = in[4*i +: 4];
    end
end
~~~

这里 i 是索引，sel 是输入选择信号。不能写成给 sel 赋值。

### 9.1 向量倒序

循环也可以用于把向量的位顺序反过来：

~~~verilog
integer i;

always @(*) begin
    for (i = 0; i < 100; i = i + 1)
        out[i] = in[99-i];
end
~~~

这表示：

~~~text
out[0]  = in[99]
out[1]  = in[98]
...
out[99] = in[0]
~~~

循环边界要和向量宽度匹配，避免数组越界。

### 9.2 统计 1 的个数

可以先给结果清零，再逐位累加：

~~~verilog
integer i;

always @(*) begin
    out = 8'd0;
    for (i = 0; i < 255; i = i + 1)
        out = out + in[i];
end
~~~

因为 `in[i]` 是 1 位信号，所以它对 `out` 的贡献只有 0 或 1。结果位宽需要足够表示最大计数值。

### 9.3 `generate for`：生成重复硬件

过程 `for` 写在 `always` 中，用来描述一个过程块内的组合行为；`generate for` 在编译和展开阶段生成多个模块实例或硬件结构。

~~~verilog
genvar i;

generate
    for (i = 0; i < 100; i = i + 1) begin : gen_fa
        if (i == 0) begin : gen_first
            full_adder u_fa(
                .a(a[i]), .b(b[i]), .cin(cin),
                .sum(sum[i]), .cout(cout[i])
            );
        end else begin : gen_rest
            full_adder u_fa(
                .a(a[i]), .b(b[i]), .cin(cout[i-1]),
                .sum(sum[i]), .cout(cout[i])
            );
        end
    end
endgenerate
~~~

`genvar` 是生成循环的索引，生成块最好有名字，例如 `gen_fa`。当第一位和后续位的连接方式不同时，可以用 `if ... else` 生成两个分支。

---

## 十、条件运算符 ?:

语法：

~~~verilog
条件 ? 条件为真时的值 : 条件为假时的值
~~~

例如 2 选 1 多路选择器：

~~~verilog
assign out = sel ? b : a;
~~~

等价于：

~~~verilog
always @(*) begin
    if (sel)
        out = b;
    else
        out = a;
end
~~~

条件运算符适合简单组合选择逻辑。

---

## 十一、归约运算符

归约运算符把整个向量压缩成 1 位结果：

~~~verilog
&a    // a 的所有位进行 AND
|a    // a 的所有位进行 OR
^a    // a 的所有位进行 XOR
~&a   // 归约 NAND
~|a   // 归约 NOR
~^a   // 归约 XNOR
~~~

例如：

~~~verilog
assign all_one = &in;
assign any_one = |in;
assign parity  = ^in;
~~~

区别：

~~~verilog
a & b   // 输出仍然可能是多位向量
&a      // 输出一定是 1 位
~~~

---

## 十二、模块层次和模块例化

### 12.1 定义子模块

~~~verilog
module and_gate(
    input  a,
    input  b,
    output out
);

    assign out = a & b;

endmodule
~~~

### 12.2 按名称连接端口

~~~verilog
and_gate u1(
    .a(a),
    .b(b),
    .out(out)
);
~~~

左侧是子模块端口名，右侧是当前模块中的信号名。

### 12.3 按位置连接端口

~~~verilog
and_gate u1(a, b, out);
~~~

这种写法依赖端口顺序，端口较多时容易接错。推荐使用命名连接。

### 12.4 实例名必须不同

~~~verilog
full_adder fa0(...);
full_adder fa1(...);
full_adder fa2(...);
~~~

fa0、fa1、fa2 是 3 个不同实例名。

### 12.5 中间信号

~~~verilog
wire carry1;
~~~

模块之间需要连接时，使用内部 wire：

~~~verilog
some_module u1(.out(carry1));
some_module u2(.in(carry1));
~~~

### 12.6 使用已有模块搭建更大的加法器

如果 HDLBits 已经提供 `add16` 模块，就可以把两个 16 位加法器连接成 32 位加法器：

~~~verilog
wire carry16;
wire unused_cout;

add16 u_low(
    .a(a[15:0]),
    .b(b[15:0]),
    .cin(1'b0),
    .sum(sum[15:0]),
    .cout(carry16)
);

add16 u_high(
    .a(a[31:16]),
    .b(b[31:16]),
    .cin(carry16),
    .sum(sum[31:16]),
    .cout(unused_cout)
);
~~~

低 16 位产生的 `carry16` 必须连接到高 16 位的 `cin`。即使最终进位没有连接到输出，也必须连接到一个信号，例如 `unused_cout`，避免端口悬空。

### 12.7 Carry-select adder 的思想

选择进位加法器会对高位部分分别计算两种情况：

1. 假设低位进位为 0，计算一次高位结果。
2. 假设低位进位为 1，再计算一次高位结果。
3. 根据低位实际产生的进位，用 MUX 选出正确结果。

结构示意：

~~~text
低 16 位加法器 ── carry16 ──┐
                              ├─ MUX ── 高 16 位结果
高 16 位(cin=0) ──────────────┘
高 16 位(cin=1) ──────────────┘
~~~

对应的选择逻辑可以写成：

~~~verilog
assign upper_sum = carry16 ? upper_sum_c1 : upper_sum_c0;
~~~

它的目的不是改变加法结果，而是减少等待进位传播的时间。

### 12.8 加法器和减法器

二进制补码减法：

~~~text
a - b = a + (~b) + 1
~~~

因此可以用一个 `sub` 信号同时控制按位取反和初始进位：

~~~verilog
wire [31:0] b_selected;

assign b_selected = b ^ {32{sub}};

add16 u_low(
    .a(a[15:0]),
    .b(b_selected[15:0]),
    .cin(sub),
    .sum(sum[15:0]),
    .cout(carry16)
);
~~~

当 `sub = 0` 时：

~~~text
b_selected = b，cin = 0，因此执行 a + b
~~~

当 `sub = 1` 时：

~~~text
b_selected = ~b，cin = 1，因此执行 a + ~b + 1，也就是 a - b
~~~

`{32{sub}}` 是复制运算符：`sub` 为 1 时得到 32 位全 1，为 0 时得到 32 位全 0。

---

## 十三、多路选择器 MUX

多路选择器根据选择信号，从多个输入中选出一个输入。

### 13.1 2 选 1

~~~verilog
assign out = sel ? b : a;
~~~

### 13.2 向量 MUX

如果 a、b、out 都是 4 位，条件运算符会选择完整的 4 位向量：

~~~verilog
assign out[3:0] = sel ? b[3:0] : a[3:0];
~~~

### 13.3 256 选 1、每路 4 位

输入总宽度为 1024 位：

~~~text
256 × 4 = 1024
~~~

题目规定：

~~~text
sel = 0 → in[3:0]
sel = 1 → in[7:4]
sel = 2 → in[11:8]
~~~

最简洁写法：

~~~verilog
assign out = in[sel * 4 +: 4];
~~~

其中：

- sel * 4 是被选择分组的起始位
- +: 4 表示向高位取 4 位
- 选择宽度固定为 4 位

按你的 always + for 写法：

~~~verilog
module top_module(
    input  [1023:0] in,
    input  [7:0]    sel,
    output reg [3:0] out
);

    integer i;

    always @(*) begin
        out = 4'b0000;

        for (i = 0; i < 256; i = i + 1) begin
            if (sel == i)
                out = in[4*i +: 4];
        end
    end

endmodule
~~~

### 13.4 原代码中的错误

原写法：

~~~verilog
alway @(*)
~~~

应改成：

~~~verilog
always @(*)
~~~

原写法：

~~~verilog
sel = sel_out;
~~~

不能给输入 sel 赋值。

原写法：

~~~verilog
out = in[4+i;0];
~~~

括号和分隔符错误，正确的索引位选写法是：

~~~verilog
out = in[4*i +: 4];
~~~

---

## 十四、半加器

半加器把两个 1 位输入相加：

~~~text
a + b
~~~

输出：

- sum：结果位
- cout：进位位

逻辑表达式：

~~~verilog
sum  = a ^ b;
cout = a & b;
~~~

完整模块：

~~~verilog
module half_adder(
    input  a,
    input  b,
    output sum,
    output cout
);

    assign sum  = a ^ b;
    assign cout = a & b;

endmodule
~~~

真值表：

| a | b | sum | cout |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |
| 0 | 1 | 1 | 0 |
| 1 | 0 | 1 | 0 |
| 1 | 1 | 0 | 1 |

---

## 十五、全加器

全加器比半加器多一个输入进位 cin：

~~~text
a + b + cin
~~~

逻辑表达式：

~~~verilog
sum  = a ^ b ^ cin;
cout = (a & b) | (a & cin) | (b & cin);
~~~

完整模块，使用 always 写法：

~~~verilog
module full_adder(
    input  a,
    input  b,
    input  cin,
    output reg sum,
    output reg cout
);

    always @(*) begin
        sum  = a ^ b ^ cin;
        cout = (a & b) | (a & cin) | (b & cin);
    end

endmodule
~~~

也可以使用连续赋值：

~~~verilog
module full_adder(
    input  a,
    input  b,
    input  cin,
    output sum,
    output cout
);

    assign sum  = a ^ b ^ cin;
    assign cout = (a & b) | (a & cin) | (b & cin);

endmodule
~~~

如果使用加法运算符，还可以写成：

~~~verilog
assign {cout, sum} = a + b + cin;
~~~

这里 {cout, sum} 是 2 位拼接结果。

真值表：

| a | b | cin | sum | cout |
|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 | 0 |
| 0 | 0 | 1 | 1 | 0 |
| 0 | 1 | 0 | 1 | 0 |
| 0 | 1 | 1 | 0 | 1 |
| 1 | 0 | 0 | 1 | 0 |
| 1 | 0 | 1 | 0 | 1 |
| 1 | 1 | 0 | 0 | 1 |
| 1 | 1 | 1 | 1 | 1 |

进位 cout 的规律是：三个输入中至少有两个为 1 时，cout = 1。

---

## 十六、Adder3：3 位串行进位加法器

题目要求使用 3 个全加器，把两个 3 位数和一个输入进位相加。每一位的进位连接到下一位的 cin。

~~~verilog
module full_adder(
    input  a,
    input  b,
    input  cin,
    output reg sum,
    output reg cout
);

    always @(*) begin
        sum  = a ^ b ^ cin;
        cout = (a & b) | (a & cin) | (b & cin);
    end

endmodule


module top_module(
    input  [2:0] a,
    input  [2:0] b,
    input        cin,
    output [2:0] cout,
    output [2:0] sum
);

    full_adder fa0(
        .a(a[0]),
        .b(b[0]),
        .cin(cin),
        .sum(sum[0]),
        .cout(cout[0])
    );

    full_adder fa1(
        .a(a[1]),
        .b(b[1]),
        .cin(cout[0]),
        .sum(sum[1]),
        .cout(cout[1])
    );

    full_adder fa2(
        .a(a[2]),
        .b(b[2]),
        .cin(cout[1]),
        .sum(sum[2]),
        .cout(cout[2])
    );

endmodule
~~~

进位链：

~~~text
cin → fa0 → cout[0] → fa1 → cout[1] → fa2 → cout[2]
~~~

其中：

- sum[0] 是最低位和
- sum[2] 是最高位和
- cout[0] 是第 0 位产生的进位
- cout[1] 是第 1 位产生的进位
- cout[2] 是最终进位

例如：

~~~text
a   = 3'b111
b   = 3'b001
cin = 0
~~~

结果是：

~~~text
sum[2:0] = 3'b000
cout[2]  = 1
~~~

因为 7 + 1 = 8，3 位结果只能保留低 3 位，最高位由最终进位 cout[2] 表示。

---

## 十七、结构化设计和行为化设计

同一个电路可以有不同写法。

### 17.1 行为化写法

直接描述功能：

~~~verilog
assign {cout, sum} = a + b + cin;
~~~

### 17.2 结构化写法

用子模块搭建电路：

~~~verilog
full_adder fa0(...);
full_adder fa1(...);
full_adder fa2(...);
~~~

Adder3 明确要求实例化全加器，因此应使用结构化写法。学习模块例化的目的，就是把复杂电路拆成可以重复使用的小模块。

---

## 十八、组合逻辑检查清单

写完组合逻辑后，可以逐项检查：

- always 是否拼写正确
- always 是否使用 @(*)
- 在 always 中赋值的输出是否声明为 reg
- 是否给输出设置了默认值
- if 是否有 else，或者是否有默认赋值
- case 是否有 default
- 是否错误地给 input 赋值
- 位宽是否匹配
- [msb:lsb] 的方向是否正确
- +: 后面的位宽是否固定
- 模块实例名是否重复
- 子模块端口连接顺序是否正确
- 多级加法器的进位是否连接到下一位
- 是否混用了连续赋值和过程赋值

---

## 十九、当前阶段应掌握的核心模板

### 简单组合逻辑

~~~verilog
module top_module(
    input  a,
    input  b,
    output out
);

    assign out = a & b;

endmodule
~~~

### always 组合逻辑

~~~verilog
module top_module(
    input      a,
    input      b,
    output reg out
);

    always @(*) begin
        out = a & b;
    end

endmodule
~~~

### 向量切片

~~~verilog
assign out = in[7:4];
~~~

### 动态固定宽度切片

~~~verilog
assign out = in[sel*4 +: 4];
~~~

### 模块例化

~~~verilog
child_module u0(
    .in_a(a),
    .in_b(b),
    .out_y(y)
);
~~~

### 组合逻辑循环

~~~verilog
integer i;

always @(*) begin
    out = 0;
    for (i = 0; i < N; i = i + 1) begin
        if (sel == i)
            out = data[i];
    end
end
~~~

---

## 二十、学习到 Adder3 后的知识边界

到这里，应该能够独立完成：

1. 使用逻辑门描述组合电路
2. 处理单个位和多位向量
3. 使用切片、拼接和重复运算符
4. 使用 assign 描述组合逻辑
5. 使用 always @(*) 描述组合逻辑
6. 使用 if、case 和 for
7. 避免组合逻辑锁存器
8. 定义和例化子模块
9. 编写 2 选 1、9 选 1、256 选 1 多路选择器
10. 编写半加器和全加器
11. 连接多个全加器组成串行进位加法器

后续 HDLBits 通常会进一步学习触发器、寄存器、计数器、移位寄存器和有限状态机。这些内容会引入时钟、状态保存、复位和更完整的时序逻辑设计。
