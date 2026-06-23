# 编译原理模拟期末卷 A
Date: 2026-06-23
Author: Yixun Hong
Tags: Compiler, Mock Final, DFA, LALR, Register Allocation
Abstract: 第一套模拟卷，覆盖词法 DFA、LL/LR、活动记录、IR 翻译、trace、指令选择、活跃分析和寄存器分配。

## 一、判断题

1. 一个正则语言一定可以由 DFA 识别。

<details>
<summary>参考答案</summary>
<p>对。正则表达式、NFA、DFA 三者表达能力等价。</p>
</details>

2. 所有 LR(1) 文法都是 LALR(1) 文法。

<details>
<summary>参考答案</summary>
<p>错。LALR(1) 会合并同 LR(0) core 的项集，可能引入 reduce/reduce 冲突。</p>
</details>

3. 在 Tiger 中 escaping 的局部变量可以安全放入 caller-save 寄存器。

<details>
<summary>参考答案</summary>
<p>错。escaping 变量需要在栈帧中有稳定地址。</p>
</details>

4. 活跃性分析是后向 may analysis。

<details>
<summary>参考答案</summary>
<p>对。只要存在一条未来路径会用到变量，该变量就在当前点活跃。</p>
</details>

## 二、选择题

1. 文法 `E -> E + T | T; T -> id` 直接用于 LL(1) 分析的问题是：

A. 存在左递归  
B. 没有终结符  
C. 没有开始符号  
D. 不是上下文无关文法

<details>
<summary>参考答案</summary>
<p>A。直接左递归会导致预测分析递归不终止。</p>
</details>

2. 在 LR parsing table 中，某状态同一终结符下既有 shift 又有 reduce，称为：

A. reduce/reduce conflict  
B. shift/reduce conflict  
C. FIRST/FOLLOW conflict  
D. type conflict

<details>
<summary>参考答案</summary>
<p>B。</p>
</details>

3. 以下哪个最适合表示 `a[i]` 的地址？

A. `BINOP(PLUS, TEMP a, BINOP(MUL, TEMP i, CONST wordSize))`  
B. `CALL(NAME a, TEMP i)`  
C. `SEQ(TEMP a, TEMP i)`  
D. `CJUMP(EQ, a, i, L1, L2)`

<details>
<summary>参考答案</summary>
<p>A。数组元素地址通常是基址加下标乘元素大小。</p>
</details>

## 三、大题

### 1. DFA 构造

构造 DFA 识别十六进制整数 token：可选前缀 `0x` 或 `0X`，之后至少一个十六进制数字；无前缀时只允许十进制数字。说明接受状态。

<details>
<summary>参考答案</summary>
<p>状态：Start、Zero、Dec、X、Hex、Dead。Start 读 0 到 Zero，读 1-9 到 Dec；Zero 读 x/X 到 X，读 digit 到 Dec，也可作为 Dec 接受；X 必须读 hex digit 到 Hex；Hex 读 hex digit 留 Hex。接受状态为 Zero、Dec、Hex。</p>
</details>

### 2. LALR(1) 分析

对 `S'->S; S->AA; A->aA|b` 构造 LR(1) 初始项集 I0，并写出 `goto(I0, A)` 与 `goto(I0, a)` 的核心。

<details>
<summary>参考答案</summary>
<p>I0 含 `[S'->.S,$]`、`[S->.AA,$]`、`[A->.aA,a/b]`、`[A->.b,a/b]`。`goto(I0,A)` core 含 `S->A.A`，closure 后加入 `A->.aA,$`、`A->.b,$`。`goto(I0,a)` core 含 `A->a.A`，closure 后加入 `A->.aA,a/b`、`A->.b,a/b`。</p>
</details>

### 3. Tiger IR

将 `for i := 0 to n do s := s + i` 翻译成 IR 控制流框架。

<details>
<summary>参考答案</summary>
<p>先初始化 `i:=0`，保存上界 `limit:=n`，然后 `LABEL test; CJUMP(LE,i,limit,body,done); LABEL body; MOVE(s,s+i); CJUMP(LT,i,limit,inc,done); LABEL inc; MOVE(i,i+1); JUMP test; LABEL done`。上界应只求值一次。</p>
</details>

### 4. 活跃分析与相干图

对 `a<-1; b<-2; c<-a+b; d<-c+b; return d` 求 live-out，并画相干边。

<details>
<summary>参考答案</summary>
<p>从后往前：return 前 live-in={d}；`d<-c+b` live-in={b,c} live-out={d}；`c<-a+b` live-in={a,b} live-out={b,c}；`b<-2` live-in={a} live-out={a,b}；`a<-1` live-in=empty live-out={a}。定义点与 live-out 建边：d 与 live-out 空外无新增；c 与 b 相干；b 与 a 相干；a 无。主要边为 (a,b),(b,c)。</p>
</details>
