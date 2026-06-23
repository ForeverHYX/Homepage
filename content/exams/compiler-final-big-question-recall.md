# 编译原理期末大题回忆卷
Date: 2024-06-21
Author: Yixun Hong
Tags: Compiler, Recall, Big Questions, Tiger
Abstract: 根据考后记忆整理的大题方向，保留原始回忆顺序，并补成可以直接练习的完整题干。

## 说明

这份是“原来那份回忆卷”的独立版本，只围绕记住的大题，不含 PDF 小题。题目按回忆补全，适合快速过一遍大题套路。

## 1. 有符号数（浮点数与指数）的 DFA

请构造 DFA 识别有符号数 token：`+12`、`-0.5`、`.25`、`3.`、`2e10`、`-6.02E+23` 合法；`+`、`.`、`e10`、`1e`、`1e+` 非法。写出状态集合、接受状态和转移。

<details>
<summary>参考答案</summary>
<p>核心状态：Start、Sign、Int、DotNoInt、Frac、ExpMark、ExpSign、ExpInt、Dead。接受状态是 Int、Frac、ExpInt。Start 读 sign 到 Sign，读 digit 到 Int，读 dot 到 DotNoInt；Sign 同 Start 但不可再读 sign；Int 读 digit 留 Int，dot 到 Frac，e/E 到 ExpMark；DotNoInt 必须读 digit 到 Frac；Frac 读 digit 留 Frac，e/E 到 ExpMark；ExpMark 可读 sign 到 ExpSign 或 digit 到 ExpInt；ExpSign 必须读 digit 到 ExpInt；ExpInt 读 digit 留 ExpInt。</p>
</details>

## 2. LALR(1) DFA 和 parsing table

对文法 `S' -> S; S -> C C; C -> c C | d` 构造 LR(1) 项集族，合并同 LR(0) core 的项得到 LALR(1) DFA，并写出 ACTION/GOTO 表。

<details>
<summary>参考答案</summary>
<p>先从 `[S' -> .S, $]` closure，得到 `S -> .CC,$` 与 `C -> .cC, c/d`、`C -> .d, c/d` 等项；goto 生成若干状态。LALR 合并时只合并 core 相同的状态，lookahead 取并集。该文法是常见 LR/LALR 练习，无冲突。表中状态含 `C -> d .` 时在对应 lookahead 上 reduce，含 `C -> c . C` 时 goto C，含 `S' -> S .` 时 `$` accept。</p>
</details>

## 3. static link 和 display

给定嵌套函数：`f` 内定义 `g`，`g` 内定义 `h`。`h` 访问 `f` 的局部变量 x 和 `g` 的局部变量 y。画出 static link 链，并说明 display 如何访问 x/y。

<details>
<summary>参考答案</summary>
<p>调用 h 时，h 的 static link 指向最近一次 g 的帧，g 的 static link 指向最近一次 f 的帧。h 访问 y：沿一条 static link 到 g 帧再加偏移；访问 x：沿两条 static link 到 f 帧再加偏移。display 则保存每个词法层级当前活动帧 fp，h 访问 y 直接取 display[level(g)]，访问 x 取 display[level(f)]。</p>
</details>

## 4. 给定 Tiger 语法做 IR 翻译

把 `if a < b then x := a + 1 else x := b + 1` 翻译成 Tree IR。要求使用 `CJUMP`、`LABEL`、`JUMP`、`MOVE`，并避免 fall-through 语义不清。

<details>
<summary>参考答案</summary>
<p>参考结构：`CJUMP(LT,a,b,Ltrue,Lfalse); LABEL Ltrue; MOVE(x,BINOP(PLUS,a,CONST 1)); JUMP Ldone; LABEL Lfalse; MOVE(x,BINOP(PLUS,b,CONST 1)); JUMP Ldone; LABEL Ldone`。若表达式有值而非语句，可先分配临时 t，在两个分支中 `MOVE(t,...)`，最后以 `ESEQ` 或规范化后的临时量表示结果。</p>
</details>

## 5. 画 basic block 并找最长 trace

对线性语句 `L0: a:=0; L1: if a<n goto L2 else L5; L2: b:=b+a; L3: a:=a+1; jump L1; L5: return b` 划分基本块，画 CFG，并选择一条最长 trace。

<details>
<summary>参考答案</summary>
<p>基本块：B0=`L0,a:=0,jump L1`（规范化时补跳转）；B1=`L1,CJUMP`; B2=`L2,b:=b+a; L3,a:=a+1; JUMP L1`; B5=`L5,return`。CFG：B0->B1，B1->B2/B5，B2->B1。最长 trace 通常选热循环路径 `B0 -> B1 -> B2`，然后下一轮 B1 已在 trace 中，退出另起 `B5`。</p>
</details>

## 6. maximal munch 指令选择

对 `MOVE(MEM(BINOP(PLUS, TEMP fp, CONST -16)), BINOP(MUL, TEMP a, CONST 4))`，在支持 `store M[base+k] <- r`、`muli r <- r,k` 的机器上用 maximal munch 生成指令。

<details>
<summary>参考答案</summary>
<p>最大匹配左侧寻址模式为 `M[fp-16]`，右侧乘法可匹配 `muli t <- a, 4`。最终：`muli t <- a, 4; store M[fp-16] <- t`。若目标机器有带 scale 的 store 模板，则 maximal munch 会选择更大模板。</p>
</details>

## 7. 活跃分析

对 `1:a<-b+c; 2:d<-a+e; 3:if d goto 1; 4:return a`，写出数据流方程并求 in/out 集。

<details>
<summary>参考答案</summary>
<p>方程：`in[n]=use[n]∪(out[n]-def[n])`，`out[n]=∪in[succ[n]]`。succ：1->2，2->3，3->1/4，4->exit。固定点可得：in4={a}, out4=empty；in3={a,b,c,d,e}, out3={a,b,c,e}；in2={a,b,c,e}, out2={a,b,c,d,e}；in1={b,c,e}, out1={a,b,c,e}。</p>
</details>

## 8. 寄存器分配（priority 计算与选择）

给定 K=3，临时变量 spill cost：`t1=20,t2=12,t3=8,t4=4,t5=2`；相干边：`t1-t2,t1-t3,t1-t4,t2-t3,t2-t5,t3-t4,t4-t5`。计算 `cost/degree` priority，并选择潜在 spill。

<details>
<summary>参考答案</summary>
<p>degree：t1=3,t2=3,t3=3,t4=3,t5=2。priority：t1=6.67,t2=4,t3=2.67,t4=1.33,t5=1。若低 priority 更适合 spill，先选 t5 或 t4；但 t5 度数小于 K，可以先 simplify，不必 spill。剩余高度数节点中 t4 priority 最低，作为潜在 spill 更合理。</p>
</details>
