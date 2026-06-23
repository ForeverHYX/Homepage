# 编译原理模拟期末卷 C
Date: 2026-06-23
Author: Yixun Hong
Tags: Compiler, Mock Final, Semantic Analysis, Allocation
Abstract: 第三套模拟卷，综合语义分析、函数调用约定、闭包访问、数据流方程和图着色寄存器分配。

## 一、判断题

1. FIRST/FOLLOW 集只用于 LL 分析，和 LR 分析完全无关。

<details>
<summary>参考答案</summary>
<p>错。LR 项 closure 中计算 lookahead 时也会用 FIRST。</p>
</details>

2. caller-save 寄存器在调用后由调用者负责保存需要的值。

<details>
<summary>参考答案</summary>
<p>对。callee-save 则由被调用者保存和恢复。</p>
</details>

3. 若两个变量从不同时 live，则它们可以分配到同一个物理寄存器。

<details>
<summary>参考答案</summary>
<p>对。这正是图着色寄存器分配利用相干图的基本依据。</p>
</details>

## 二、选择题

1. Tiger 中数组越界检查最适合放在哪个阶段附近？

A. 词法分析  
B. 语法分析  
C. IR 翻译/后续 lowering  
D. 链接阶段

<details>
<summary>参考答案</summary>
<p>C。越界检查依赖表达式值和运行时控制流，通常在 IR 翻译时显式生成或在后续 lowering 加入。</p>
</details>

2. Briggs 合并准则的直观含义是：

A. 合并后高度数邻居少于 K 个时较安全  
B. 只要两个节点有 move 边就必定合并  
C. 只检查一个节点的邻居是否都连接另一个节点  
D. 永远不合并 move-related 节点

<details>
<summary>参考答案</summary>
<p>A。C 是 George 准则的直观描述。</p>
</details>

## 三、大题

### 1. 语义分析

分析 Tiger 表达式 `let type intArray = array of int var a := intArray[10] of 0 in a[0] := "x" end`，指出类型错误位置。

<details>
<summary>参考答案</summary>
<p>`a` 的类型是 intArray，元素类型为 int。`a[0] := "x"` 左侧元素类型为 int，右侧字符串类型为 string，赋值类型不匹配。数组创建 `intArray[10] of 0` 本身合法。</p>
</details>

### 2. 函数调用与 static link

函数 `f` 定义在最外层，`g` 定义在 `f` 内，`h` 定义在 `g` 内。若 `f` 调用 `g`，`g` 调用 `h`，分别传递哪些 static link？

<details>
<summary>参考答案</summary>
<p>调用 g 时，g 的 static link 指向当前 f 的帧。调用 h 时，h 的 static link 指向当前 g 的帧。若 h 内访问 f 的变量，则从 h 帧沿 static link 到 g，再到 f。</p>
</details>

### 3. 数据流分析

给定 CFG：B1->B2,B1->B3,B2->B4,B3->B4。各块 `use/def` 为：B1 use={},def={a}; B2 use={a},def={b}; B3 use={a},def={c}; B4 use={b,c},def={d}。求 live-in/live-out。

<details>
<summary>参考答案</summary>
<p>B4: in={b,c}, out=empty。B2: out={b,c}, in={a,c}。B3: out={b,c}, in={a,b}。B1: out=in(B2)∪in(B3)={a,b,c}，in=out-def={b,c}。这里 b/c 在不同分支中未必都已定义，实际编译器通常先经 SSA/检查处理；作为保守 may analysis，会取并集。</p>
</details>

### 4. 图着色寄存器分配

K=3，相干边为 `(a,b),(a,c),(a,d),(b,c),(c,d),(d,e)`，move 边为 `(b,d)`。说明 simplify、coalesce、freeze、spill 的一次可能过程。

<details>
<summary>参考答案</summary>
<p>度数：a=3,b=2,c=3,d=3,e=1。先 simplify 低度数 e、b（若 b move-related 可暂缓）。尝试合并 b,d：按 Briggs 看合并后高度数邻居数量是否小于 K；按 George 看 b 的高阶邻居是否与 d 相邻。若不安全则 freeze b-d 的 move，再 simplify b。若剩余全为高度数，按 spill priority 选最低成本节点作为潜在 spill。select 阶段逆序着色，若潜在 spill 有可用颜色则不真正 spill。</p>
</details>

### 5. IR 到汇编

为 `CALL(NAME print_int, [MEM(BINOP(PLUS, TEMP fp, CONST -8))])` 生成一段调用约定友好的伪汇编。

<details>
<summary>参考答案</summary>
<p>先取参数：`load r_arg0 <- M[fp-8]`；按调用约定放入参数寄存器或参数栈槽；保存调用者需要的 caller-save；执行 `call print_int`；恢复需要的 caller-save。若返回值不用，可忽略返回寄存器。</p>
</details>
