# 编译原理模拟期末卷 B
Date: 2026-06-23
Author: Yixun Hong
Tags: Compiler, Mock Final, IR, Trace, GC
Abstract: 第二套模拟卷，偏中后端：规范化、basic block、trace scheduling、指令选择、循环优化和垃圾回收。

## 一、选择题

1. `ESEQ(s,e)` 的主要含义是：

A. 先执行语句 s，再计算表达式 e  
B. 同时执行 s 和 e  
C. 删除 s，只保留 e  
D. 表示一个基本块

<details>
<summary>参考答案</summary>
<p>A。</p>
</details>

2. basic block 的最后一条语句通常是：

A. LABEL  
B. JUMP/CJUMP/RETURN  
C. MOVE  
D. BINOP

<details>
<summary>参考答案</summary>
<p>B。基本块中间不能有跳转，入口通常是 label，出口通常是跳转或返回。</p>
</details>

3. copying collection 相比 mark-sweep 的优势之一是：

A. 不需要 root set  
B. 可以压缩存活对象，减少外部碎片  
C. 无需移动对象  
D. 不能处理循环引用

<details>
<summary>参考答案</summary>
<p>B。</p>
</details>

## 二、大题

### 1. 正则树规范化

规范化 `BINOP(PLUS, ESEQ(MOVE(TEMP a, CONST 1), TEMP a), CALL(NAME f, []))`，要求 CALL 不作为普通表达式深嵌。

<details>
<summary>参考答案</summary>
<p>先提升左侧 ESEQ：执行 `MOVE(a,1)` 后表达式为 `BINOP(PLUS,TEMP a,CALL(...))`。再将 CALL 提升到临时量：`MOVE(tcall, CALL(NAME f, [])); BINOP(PLUS,TEMP a,TEMP tcall)`。最终语句序列先 `MOVE(a,1)`，再 `MOVE(tcall,CALL(...))`，表达式使用 `tcall`。</p>
</details>

### 2. Trace scheduling

给定 CFG 边：B1->B2/B3，B2->B4，B3->B4，B4->B5/B6，B5->B7，B6->B7。选择 trace 并说明如何处理条件跳转 fall-through。

<details>
<summary>参考答案</summary>
<p>可选最长 trace `B1,B2,B4,B5,B7`。条件跳转尽量重排为常见路径 fall-through；若原 CJUMP 的 true/false 与布局不符，可交换条件或插入补偿 JUMP。未纳入 trace 的 B3、B6 另排。</p>
</details>

### 3. Maximal munch 与 dynamic programming

同一棵树若 maximal munch 得到代价 4，动态规划得到代价 3，说明原因，并给出何时仍会使用 maximal munch。

<details>
<summary>参考答案</summary>
<p>maximal munch 贪心选择当前最大模板，可能阻塞子树的更优组合；动态规划自底向上比较所有模板组合可得全局最优。maximal munch 实现简单、速度快，若指令集规则简单或编译速度优先仍可使用。</p>
</details>

### 4. 循环不变式外提

循环中有 `t <- a * 4; x <- M[base+t]; i <- i+1`，其中 a 在循环内无定义。哪些语句可外提？需要满足什么安全条件？

<details>
<summary>参考答案</summary>
<p>`t <- a*4` 是循环不变，可外提到 preheader。`x <- M[base+t]` 是否外提取决于内存是否可能在循环中被写、base 是否变化、该 load 是否会引发异常等。安全外提需支配所有使用且不改变异常/内存语义。</p>
</details>
