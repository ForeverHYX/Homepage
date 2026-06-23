# 23-24 编译原理期末回忆卷（小题 + 大题补全版）
Date: 2024-06-20
Author: Yixun Hong
Tags: Compiler, Final, Recall, Tiger
Abstract: 根据 23-24 学年编译原理回忆卷 PDF 的小题部分整理，并按回忆补全大题题干。PDF 中缺失的单选题题干或选项已按课堂常见考点补全，便于完整自测。

## 使用说明

- 判断题与选择题来自回忆 PDF；原 PDF 标注“忘了”的位置已按知识点补全。
- 大题根据回忆点补成可做题目，答案给的是参考步骤，不是唯一写法。
- 每题下方都有折叠答案；先做完再展开。

## 一、判断题

1. 将有 n 个状态的 NFA 通过子集构造的方法转为 DFA 时，构造出的 DFA 最多有 2^n 个状态。

<details>
<summary>参考答案</summary>
<p>对。子集构造的 DFA 状态是 NFA 状态集合的子集，最多有 2^n 个。</p>
</details>

2. 正则表达式 `"/*" "/"* ( [^*/] | [^*]"/" | "*"[^/] )* "*"* "*/"` 可以识别所有 C 风格注释。

<details>
<summary>参考答案</summary>
<p>错。C 风格注释要求从 /* 到第一个 */ 结束，不能简单认为该表达式覆盖所有边界情况；课堂中常强调注释识别要避免把中间的 */ 吞掉。</p>
</details>

3. 上下文无关文法 `S -> (S)S | ε` 是 LL(1) 的。

<details>
<summary>参考答案</summary>
<p>对。`FIRST((S)S) = {(}`，`FIRST(ε) = {ε}`，且 `FOLLOW(S)` 中的符号与 `(` 不冲突，可以用一个向前看符号预测。</p>
</details>

4. 一般情况下，不考虑使用散列表作为命令式符号表的实现。

<details>
<summary>参考答案</summary>
<p>错。命令式符号表常用散列表配合作用域栈实现；函数式符号表更偏向持久化树结构。</p>
</details>

5. 嵌套函数用于访问外层函数局部变量的 static link 在运行时指向其调用者的栈帧。

<details>
<summary>参考答案</summary>
<p>错。static link 指向词法外层函数的栈帧，不一定是调用者；dynamic link 才反映调用者。</p>
</details>

6. 访问 escaping variable 时，应当在寄存器中寻找。

<details>
<summary>参考答案</summary>
<p>错。escaping variable 需要放在栈帧中，供内部函数或越过作用域的访问使用。</p>
</details>

7. display 是一个维护 fp 的数组。

<details>
<summary>参考答案</summary>
<p>对。display 通常按词法层级保存对应活动记录的 frame pointer，用于快速访问外层变量。</p>
</details>

8. 语法分析、词法分析、语义分析是编译器前端的任务。

<details>
<summary>参考答案</summary>
<p>对。前端负责从源程序到抽象语法树/中间表示前的分析工作。</p>
</details>

9. 指令选择的任务是根据中间代码生成有最少指令数的机器指令序列。

<details>
<summary>参考答案</summary>
<p>错。指令选择通常优化代价，不一定等价于最少指令数；不同指令代价、寻址模式和后续寄存器分配都会影响选择。</p>
</details>

10. maximal munch 算法可以产生 optimum tiling。

<details>
<summary>参考答案</summary>
<p>错。maximal munch 是贪心算法，通常快但不保证全局最优；动态规划才用于 optimum tiling。</p>
</details>

11. 进行变量活性分析时，需要以从未来到过去的方向进行分析。

<details>
<summary>参考答案</summary>
<p>对。活跃性是后向数据流问题，`in[n]` 依赖 `out[n]`，`out[n]` 依赖后继的 `in`。</p>
</details>

12. 数据流分析时，数据流方程的解是一个保守估计。

<details>
<summary>参考答案</summary>
<p>对。编译器宁可多认为一些变量活跃/可达，也不能漏掉真实情况。</p>
</details>

13. 将中间代码树转化为正则树时会将所有 CALL 指令消去。

<details>
<summary>参考答案</summary>
<p>错。规范化会把 CALL 移到安全位置，例如包进 ESEQ/MOVE 临时量，但 CALL 本身仍然存在。</p>
</details>

14. 节点 d 支配节点 n 的充分条件是，某一条从入口 s0 到 n 的路径经过 d。

<details>
<summary>参考答案</summary>
<p>错。支配要求所有从入口到 n 的路径都经过 d，而不是存在一条路径。</p>
</details>

15. 当 x != z 时，`MOVE(MEM(x), y)` 和 `MEM(z)` 是可交换的。

<details>
<summary>参考答案</summary>
<p>通常按课堂简化假设为对。若 x 与 z 表示不同地址，写 MEM(x) 不影响读 MEM(z)。真实编译器还要考虑别名分析。</p>
</details>

16. 若 e1 与 s 可交换，则 `[e1, e2, ESEQ(s, e3)]` 与 `[SEQ(MOVE(t, e1), s), t, e2, e3]` 等价。

<details>
<summary>参考答案</summary>
<p>错。规范化列表时若 e1 与 s 可交换，可以保持 e1 在前；若不可交换才需要引入临时量保存 e1。题中把条件和变换方向混淆了。</p>
</details>

17. 在依照含 move-related node 的相干图进行寄存器分配时，当简化和合并都无法进行时，应进行 spill 操作。

<details>
<summary>参考答案</summary>
<p>错。典型算法还会先 freeze move-related node，冻结后再继续 simplify；spill 是更靠后的选择。</p>
</details>

18. 在含 move-related node 的相干图中，若 `(a,b)` 是 MOVE 边，且对每个 a 的相邻节点 t，t 与 b 相邻或 t 为不重要节点，则 a 与 b 可以合并。

<details>
<summary>参考答案</summary>
<p>对。这是 George 合并准则的表述之一。</p>
</details>

19. Mark & Sweep 算法无法回收引用计数等于 0 的对象。

<details>
<summary>参考答案</summary>
<p>错。引用计数为 0 的对象不可达，mark-sweep 可以回收；mark-sweep 的优势之一是能处理循环引用。</p>
</details>

20. BFS 比 DFS 造成更多的 cache miss。

<details>
<summary>参考答案</summary>
<p>一般按课堂讨论为对。BFS 的访问前沿更分散，局部性通常弱于沿路径深入的 DFS；具体仍依赖图存储布局。</p>
</details>

## 二、单项选择题

1. 一个 DFA 的状态表示读入二进制串后对 m 的余数，起始状态和接受状态均为余数 0。若状态集合为 `{0,1,2}`，读入 `0` 时转到 `(2r) mod m`，读入 `1` 时转到 `(2r+1) mod m`，该 DFA 识别哪些字符串？

A. 所表示数字能被 2 整除的二进制串  
B. 所表示数字能被 3 整除的二进制串  
C. 所表示数字能被 5 整除的二进制串  
D. 所表示数字能被 7 整除的二进制串

<details>
<summary>参考答案</summary>
<p>B。三个余数状态且转移按二进制追加位更新余数，接受余数 0，即识别能被 3 整除的二进制串。</p>
</details>

2. 给定文法 `exp -> exp addop term | term; addop -> "+" | "-"; term -> term mulop factor | factor; mulop -> "*"; factor -> "(" exp ")" | NUM`，求非终结符 `factor` 的 FIRST 集和 FOLLOW 集。

A. FIRST = `{ "(", NUM }`，FOLLOW = `{ "*", "+", "-", ")", $ }`  
B. FIRST = `{ NUM }`，FOLLOW = `{ "+", "-", $ }`  
C. FIRST = `{ "(", NUM }`，FOLLOW = `{ "+", "-", ")" }`  
D. FIRST = `{ "(", ")" }`，FOLLOW = `{ "*", $ }`

<details>
<summary>参考答案</summary>
<p>A。`factor` 可推出括号表达式或 NUM。它出现在 `term -> term mulop factor` 和 `term -> factor`，因此后面可跟乘号、加减、右括号或输入结束。</p>
</details>

3. 给定 LR parsing table，对文法 `S -> (S)S | ε`，当栈为 `#0(2S3)4S5`、输入为 `$` 时，进行一步操作后的栈顶为哪一项？

A. `S5`  
B. `S3`  
C. `S2`  
D. `S1`

<details>
<summary>参考答案</summary>
<p>A。状态 5 遇到 `$` 按表对 `S -> (S)S` 规约，弹出右部对应符号后 goto 回到新的 S 状态；回忆表中该题选项的栈顶为 `S5`。</p>
</details>

4. 在 yacc 产生式 `exp: exp PLUS pos exp` 中，`pos` 的语义值用哪个符号表示？

A. `$4`  
B. `$3`  
C. `$2`  
D. `$1`

<details>
<summary>参考答案</summary>
<p>B。产生式右部从 1 开始计数：第 1 个 exp 是 `$1`，PLUS 是 `$2`，pos 是 `$3`，最后的 exp 是 `$4`。</p>
</details>

5. LR parsing 中不涉及以下哪个操作？

A. shift  
B. accept  
C. reduce  
D. match

<details>
<summary>参考答案</summary>
<p>D。LR parser 的动作是 shift/reduce/accept/error；match 是 LL 预测分析里常见的终结符匹配动作。</p>
</details>

6. 访问在内存中的局部变量，需要用其在栈帧中的偏移量加上哪个基址？

A. fp  
B. sp  
C. static link  
D. global pointer

<details>
<summary>参考答案</summary>
<p>A。Tiger/Appel 风格中帧内变量通常用 frame pointer 加偏移访问；sp 会随压栈变化。</p>
</details>

7. 在嵌套定义的函数中，内层函数访问外层函数局部变量主要依赖哪一项？

A. fp  
B. sp  
C. static link  
D. return address

<details>
<summary>参考答案</summary>
<p>C。static link 串起词法外层活动记录，用于访问非局部变量。</p>
</details>

8. 以下哪项内容可能出现在函数的栈帧中？

A. 保存的 fp  
B. sp 寄存器本身  
C. static variable 的存储本体  
D. global variable 的存储本体

<details>
<summary>参考答案</summary>
<p>A。栈帧中可保存旧 fp、返回地址、形参、逃逸局部变量、callee-save 寄存器等；静态/全局变量通常不在普通函数栈帧中。</p>
</details>

9. 函数式符号表通常使用哪种效率较高的数据结构？

A. 平衡二叉搜索树  
B. 线性数组  
C. 单链表  
D. 栈上临时数组

<details>
<summary>参考答案</summary>
<p>A。函数式符号表需要持久化和共享旧版本，平衡树更自然；命令式符号表常用散列表。</p>
</details>

10. Tiling 是将正则树覆盖为机器指令模板的过程，这一过程与以下哪项最无关？

A. 机器指令模板  
B. maximal munch  
C. 树文法  
D. 最终物理寄存器分配

<details>
<summary>参考答案</summary>
<p>D。tiling 属于指令选择；物理寄存器分配通常在其后处理，虽会影响最终代码质量，但不是 tiling 本身。</p>
</details>

11. 使用动态规划法对正则树分片时，不会使用以下哪种方法？

A. minimal munch  
B. bottom-up computing  
C. optimum solution  
D. tiny tiling

<details>
<summary>参考答案</summary>
<p>A。动态规划自底向上计算最优代价；minimal munch 不是该算法的标准组成。</p>
</details>

12. Tree Grammar 主要用于哪种算法/工具？

A. fast tiling  
B. maximal munch  
C. optimal tiling / code-generator generator  
D. lexical scanner

<details>
<summary>参考答案</summary>
<p>C。树文法描述 IR 树到指令的模板，可被代码生成器生成工具用于 optimal tiling。</p>
</details>

13. 活性分析中不需要直接用到以下哪一项？

A. use[n]  
B. def[n]  
C. pred[n]  
D. succ[n]

<details>
<summary>参考答案</summary>
<p>C。标准方程是 `in[n] = use[n] ∪ (out[n] - def[n])`，`out[n] = ∪ in[s]` for `s in succ[n]`，不直接使用 pred。</p>
</details>

14. 相干图（interference graph）的主要用途是什么？

A. 描述变量之间不能分配到同一寄存器的冲突关系  
B. 描述 CFG 中基本块之间的跳转关系  
C. 描述语法分析中的移进/规约冲突  
D. 描述对象之间的引用关系

<details>
<summary>参考答案</summary>
<p>A。相干图中相邻节点表示两个 temporaries 同时活跃，不能使用同一个寄存器。</p>
</details>

15. 以下哪个树是正则树（canonical tree）？

A. `BINOP(PLUS, TEMP a, CONST 1)`  
B. `MOVE(MEM(CALL(NAME f, args)), TEMP a)`  
C. `ESEQ(MOVE(TEMP t, CONST 1), TEMP t)`  
D. `SEQ(MOVE(TEMP a, CONST 1), MOVE(TEMP b, CONST 2))`

<details>
<summary>参考答案</summary>
<p>A。正则树中不应含 ESEQ/SEQ，CALL 也需要被提升到安全位置。纯 BINOP 表达式是合法正则树。</p>
</details>

16. 一段机器指令中有 k 个 CJUMP 指令（k >= 1），则该段代码至少有多少个基本块？

A. k  
B. k + 1  
C. 2k  
D. 2k + 1

<details>
<summary>参考答案</summary>
<p>B。每个条件跳转至少结束一个基本块，并产生后续入口；最少情况下 k 个条件跳转串接形成 k+1 个块。</p>
</details>

17. 以下哪个将树转为正则树的过程是正确的？

A. 将 `BINOP(op, ESEQ(s,e), r)` 变为 `ESEQ(s, BINOP(op,e,r))`，并继续处理交换性  
B. 保留 `CJUMP` 中的任意 `ESEQ`，因为 CJUMP 不是表达式  
C. 将 `ESEQ(s1, ESEQ(s2,e))` 原样保留到指令选择阶段  
D. 将所有 `JUMP` 删除，只保留 label

<details>
<summary>参考答案</summary>
<p>A。规范化的核心是把 ESEQ 中的语句向外提升，并在必要时引入临时量保持求值顺序。</p>
</details>

18. 一条机器指令 `d <- a1 + a2` 在循环体中，以下哪种情况可以断定 `ai` 是循环内不变的？

A. `ai` 是常量  
B. 能 reach 该语句的 `ai` 的定义均在循环外  
C. `ai` 的定义中只有一条语句可以 reach 该语句  
D. 以上都不是

<details>
<summary>参考答案</summary>
<p>A 与 B 都是循环不变的典型充分条件；若本题是单选，课堂常取“以上描述中最完整的正确项”为 B。C 不够，因为唯一 reaching definition 可能在循环内。</p>
</details>

19. 以下算法中，会被 external fragmentation 影响的是哪一个？

A. Mark & Sweep  
B. 引用计数  
C. Copying collection  
D. 以上都不是

<details>
<summary>参考答案</summary>
<p>A。非移动式 mark-sweep 可能产生外部碎片；copying collection 会压缩对象。</p>
</details>

20. 给定相干图：interference 边为 `(a,b), (a,c), (b,c), (b,d), (b,e), (c,e), (d,e)`，move 边为 `(c,d)`。若要合并 c,d，能够使用哪种策略？

A. George  
B. Briggs  
C. Both  
D. Neither

<details>
<summary>参考答案</summary>
<p>A。George 准则检查 c 的高阶邻居是否也与 d 相邻；Briggs 准则检查合并后高度数邻居数是否小于 K。按常见 K=3 课堂设定，本题可用 George 而 Briggs 不一定成立。</p>
</details>

## 三、大题

### 1. 有符号数（带浮点带指数）的 DFA

构造一个 DFA，识别如下 token：可选正负号、整数部分、可选小数部分、可选指数部分。合法例子包括 `0`、`-12`、`+3.14`、`.5`、`1.`、`6.02e23`、`-1.0E-3`；非法例子包括 `+`、`.`、`1e`、`1e+`。

<details>
<summary>参考答案</summary>
<p>可设状态：S 起点；SIGN 读到正负号；INT 读到整数；DOT_NO_INT 读到无整数前缀的小数点；FRAC 读到小数；EXP 读到 e/E；EXP_SIGN 读到指数符号；EXP_INT 读到指数数字；DEAD 错误。接受状态为 INT、FRAC、EXP_INT。转移：S 遇 sign 到 SIGN，digit 到 INT，dot 到 DOT_NO_INT；SIGN 同 S 但不能再读 sign；INT 遇 digit 留 INT，dot 到 FRAC，e/E 到 EXP；DOT_NO_INT 必须读 digit 到 FRAC；FRAC 遇 digit 留 FRAC，e/E 到 EXP；EXP 可读 sign 到 EXP_SIGN 或 digit 到 EXP_INT；EXP_SIGN 必须读 digit 到 EXP_INT；EXP_INT 读 digit 留 EXP_INT。其它输入到 DEAD。</p>
</details>

### 2. LALR(1) DFA 和 parsing table

对文法 `S' -> S; S -> L = R | R; L -> * R | id; R -> L` 构造 LR(1) 项集族，合并同 LR(0) core 的项得到 LALR(1) DFA，并给出 ACTION/GOTO 表，标出是否存在冲突。

<details>
<summary>参考答案</summary>
<p>步骤：先增广文法并从 `[S' -> .S, $]` 求 closure；对每个终结符/非终结符求 goto 得到 LR(1) 项集；将 core 相同的 LR(1) 项集合并，lookahead 取并集。该经典文法是 LR(1) 且合并后仍为 LALR(1)，无 shift/reduce 或 reduce/reduce 冲突。表中 `id` 与 `*` 主要触发 shift，`=` 只在 `S -> L . = R` 项所在状态 shift，含 `R -> L .` 的状态按相应 lookahead reduce。</p>
</details>

### 3. static link 和 display

给定 Tiger 伪代码：`let function f(a:int)= let var x:=a function g(b:int)= x+b function h(c:int)= g(c)+x in h(3) end in f(2) end`。画出调用 `f -> h -> g` 时的活动记录关系，分别说明 static link 和 display 如何访问 `x`。

<details>
<summary>参考答案</summary>
<p>`f` 的帧保存 `a,x`；`g` 和 `h` 都在 f 内定义，因此它们的 static link 指向最近一次 f 的帧。调用 h 时 h 的 static link 指向 f；h 调 g 时需要把 g 的 static link 也设为 f 的帧。访问 x 时沿当前帧 static link 走到 f 的帧再加 x 的偏移。display 做法是 display[level(f)] 保存 f 的 fp，g/h 访问 x 时直接取 display 中 f 层级的 fp 再加偏移。</p>
</details>

### 4. Tiger 语法的 IR 翻译

将 Tiger 表达式 `while i < n do (a[i] := a[i] + 1; i := i + 1)` 翻译成 Tree IR，要求体现条件跳转、循环 label、数组下标地址计算和赋值。

<details>
<summary>参考答案</summary>
<p>一种参考形态：`SEQ(LABEL test, SEQ(CJUMP(LT, TEMP i, TEMP n, body, done), SEQ(LABEL body, SEQ(MOVE(MEM(BINOP(PLUS, TEMP a, BINOP(MUL, TEMP i, CONST wordSize))), BINOP(PLUS, MEM(BINOP(PLUS, TEMP a, BINOP(MUL, TEMP i, CONST wordSize))), CONST 1)), SEQ(MOVE(TEMP i, BINOP(PLUS, TEMP i, CONST 1)), SEQ(JUMP(NAME test), LABEL done))))))`。若数组有 header，需要把 base 调整为首元素地址。</p>
</details>

### 5. Basic block 和最长 trace

给定线性 IR：`LABEL L1; CJUMP(<, a, b, L2, L3); LABEL L2; MOVE(x,1); JUMP L4; LABEL L3; MOVE(x,2); LABEL L4; MOVE(y,x); CJUMP(>, y,0,L5,L6); LABEL L5; MOVE(z,y); JUMP L7; LABEL L6; MOVE(z,0); LABEL L7; RETURN z`。划分 basic blocks 并找一个最长 trace。

<details>
<summary>参考答案</summary>
<p>基本块可为：B1=`L1,CJUMP`; B2=`L2,MOVE,JUMP L4`; B3=`L3,MOVE,JUMP L4`（若原代码 fall-through 到 L4，规范化时补 JUMP）；B4=`L4,MOVE,CJUMP`; B5=`L5,MOVE,JUMP L7`; B6=`L6,MOVE,JUMP L7`; B7=`L7,RETURN`。最长 trace 可选 `B1 -> B2 -> B4 -> B5 -> B7`，或根据启发式选更可能的分支。</p>
</details>

### 6. maximal munch 指令选择

对 IR 树 `MOVE(TEMP t1, MEM(BINOP(PLUS, TEMP fp, CONST -8)))` 与 `MOVE(MEM(BINOP(PLUS, TEMP fp, CONST -12)), BINOP(PLUS, TEMP t1, CONST 1))`，用 maximal munch 在含 `load r <- M[base+k]`、`store M[base+k] <- r`、`addi r <- r+k` 的机器上生成指令。

<details>
<summary>参考答案</summary>
<p>maximal munch 尽量选择覆盖更大的寻址模式。第一棵树用 `load t1 <- M[fp-8]`。第二棵树先对右侧 `BINOP(PLUS, TEMP t1, CONST 1)` 选择 `addi r <- t1, 1`，再选择 `store M[fp-12] <- r`。若机器支持 store 立即加法结果，则可用更大模板；本题给定模板下需要临时寄存器。</p>
</details>

### 7. 活跃分析

对指令序列：`1: a <- 1; 2: b <- 2; 3: c <- a + b; 4: b <- c + a; 5: if b < 10 goto 3; 6: return b`，写出 use/def/succ，并迭代求每条指令的 in/out。

<details>
<summary>参考答案</summary>
<p>`use/def`：1 def a；2 def b；3 use a,b def c；4 use c,a def b；5 use b；6 use b。succ：1->2,2->3,3->4,4->5,5->3/6,6->exit。固定点结果：out6=empty,in6={b}; out5={a,b},in5={a,b}; out4={a,b},in4={a,c}; out3={a,c},in3={a,b}; out2={a,b},in2={a}; out1={a},in1=empty。</p>
</details>

### 8. 带 priority 的寄存器分配

给定临时变量权重：`a: loop use 8, b: loop use 5, c: loop use 3, d: loop use 1`，相干边：`(a,b),(a,c),(b,c),(b,d),(c,d)`，机器寄存器 K=2。计算 spill priority，并说明 simplify/select/spill 的选择。

<details>
<summary>参考答案</summary>
<p>常见 priority 可取 `cost / degree`。degree：a=2,b=3,c=3,d=2；priority：a=4,b=1.67,c=1,d=0.5。低 priority 更适合 spill，因此优先考虑 d，其次 c。图中 d 度数等于 K，不能直接低度 simplify；实际算法会先移除度数小于 K 的点，若无则选择最低 priority 的 d 作为潜在 spill，继续简化。select 阶段若 d 仍可着色则不真正 spill，否则把 d 放栈帧并重写程序。</p>
</details>
