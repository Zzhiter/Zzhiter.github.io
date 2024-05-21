---
authors: Zzhiter
categories: [Go]
---

# 要点总结

panic 的时候，会调用 runtime.gopanic 函数。

我们先看看 panic 生成的汇编代码：

```
func main() {
 panic("sim lou.")
}
```

汇编代码：

```
"".main STEXT size=65 args=0x0 locals=0x18
 0x0000 00000 (panic_test1.go:3) TEXT "".main(SB), ABIInternal, $24-0
......
 0x002f 00047 (panic_test1.go:4) PCDATA $0, $0
 0x002f 00047 (panic_test1.go:4) MOVQ AX, 8(SP)
 0x0034 00052 (panic_test1.go:4) CALL runtime.gopanic(SB)
.......
```

可以看到 panic 翻译成汇编代码主要是调用了 runtime.gopanic，我们一起来看看这个方法做了什么事，如下（省略部分）

```
func gopanic(e interface{}) {
 gp := getg()
 ......
 var p _panic
 p.arg = e
 _// 头插法_
 p.link = gp._panic
 gp._panic = (*_panic)(noescape(unsafe.Pointer(&p)))

 for {
  d := gp._defer
  if d == nil {
   break
  }

  _// If defer was started by earlier panic or Goexit (and, since we're back here, that triggered a new panic),_
  _// take defer off list. The earlier panic or Goexit will not continue running._
  if d.started {
   if d._panic != nil {
    d._panic.aborted = true
   }
   d._panic = nil
   d.fn = nil
   gp._defer = d.link
   freedefer(d)
   continue
  }

  _// Mark defer as started, but keep on list, so that traceback_
  _// can find and update the defer's argument frame if stack growth_
  _// or a garbage collection happens before reflectcall starts executing d.fn._
  d.started = true

  _// Record the panic that is running the defer._
  _// If there is a new panic during the deferred call, that panic_
  _// will find d in the list and will mark d._panic (this panic) aborted._
  d._panic = (*_panic)(noescape(unsafe.Pointer(&p)))

  p.argp = unsafe.Pointer(getargp(0))
  reflectcall(nil, unsafe.Pointer(d.fn), deferArgs(d), uint32(d.siz), uint32(d.siz))
  p.argp = nil

  _// reflectcall did not panic. Remove d._
  if gp._defer != d {
   throw("bad defer entry in panic")
  }
  d._panic = nil
  d.fn = nil
  gp._defer = d.link

  _// trigger shrinkage to test stack copy. See stack_test.go:TestStackPanic_
  _//GC()_

  pc := d.pc
  sp := unsafe.Pointer(d.sp) _// must be pointer so it gets adjusted during stack copy_
  freedefer(d)
  if p.recovered {
   atomic.Xadd(&runningPanicDefers, -1)

   gp._panic = p.link
   _// Aborted panics are marked but remain on the g.panic list._
   _// Remove them from the list._
   for gp._panic != nil && gp._panic.aborted {
    gp._panic = gp._panic.link
   }
   if gp._panic == nil { _// must be done with signal_
    gp.sig = 0
   }
   _// Pass information about recovering frame to recovery._
   gp.sigcode0 = uintptr(sp)
   gp.sigcode1 = pc
   mcall(recovery)
   throw("recovery failed") _// mcall should not return_
  }
 }

 preprintpanics(gp._panic)

 fatalpanic(gp._panic) _// should not return_
 _(_int)(nil) = 0      _// not reached_
}
```

- 获取指向当前 Goroutine 的指针
- 初始化一个 panic 的基本单位 _panic，并将这个 panic 头插入当前 goroutine 的 panic 链表中。
- 获取当前 Goroutine 上挂载的 _defer（数据结构也是链表）
- 若当前存在 defer 调用，则调用 reflectcall 方法去执行先前 defer 中延迟执行的代码。**reflectcall 方法若在执行过程中需要运行 recover 将会调用 gorecover 方法。**
- 结束前，使用 preprintpanics 方法打印出所涉及的 panic 消息
- 最后调用 fatalpanic 中止应用程序，实际是执行 exit(2) 进行最终退出行为的。

通过对上述代码的执行分析，可得知 **panic 方法实际上就是处理当前 Goroutine(g) 上所挂载的 ._panic 链表**（所以无法对其他 Goroutine 的异常事件响应），然后对其所属的 defer 链表和 recover 进行检测并处理，最后调用退出命令中止应用程序。

## **恢复 recover panic**

```
func main() {
 defer func() {
  if err := recover(); err != nil {
   log.Printf("recover: %v", err)
  }
 }()
 
 panic("sim lou.")
}
```

输出结果：

```
2019/10/27 12:39:30 recover: sim lou.

Process finished with exit code 0
```

我们看汇编代码，panic 是怎么被 recover 的：

```
"".main STEXT size=118 args=0x0 locals=0x50
 ......
 0x003a 00058 (panic_test2.go:6) CALL runtime.deferprocStack(SB)
 ......
 0x005a 00090 (panic_test2.go:12) CALL runtime.gopanic(SB)
 ......
 0x0060 00096 (panic_test2.go:6) CALL runtime.deferreturn(SB)
 ......
"".main.func1 STEXT size=151 args=0x0 locals=0x40
 0x0000 00000 (panic_test2.go:6) TEXT "".main.func1(SB), ABIInternal, $64-0
 ......
 0x0026 00038 (panic_test2.go:7) CALL runtime.gorecover(SB)
 ......
 0x0092 00146 (panic_test2.go:6) JMP 0
```

通过分析底层调用，可得知主要是如下几个方法：

- runtime.deferprocStack
- runtime.gopanic
- runtime.deferreturn
- runtime.gorecover

前面我们说了简单的流程，gopanic 方法会遍历调用当前 Goroutine 下的 defer 链表，若 reflectcall 执行中遇到 recover 就会调用 gorecover 进行处理，该方法代码如下：

```
func gorecover(argp uintptr) interface{} {
 _// Must be in a function running as part of a deferred call during the panic._
 _// Must be called from the topmost function of the call_
 _// (the function used in the defer statement)._
 _// p.argp is the argument pointer of that topmost deferred function call._
 _// Compare against argp reported by caller._
 _// If they match, the caller is the one who can recover._
 gp := getg()
 p := gp._panic
 if p != nil && !p.recovered && argp == uintptr(p.argp) {
  p.recovered = true
  return p.arg
 }
 return nil
}
```

这代码，看上去挺简单的，核心就是修改 recovered 字段。该字段是用于标识当前 panic 是否已经被 recover 处理。但是这和我们想象的并不一样啊，程序是怎么从 panic 流转回去的呢？是不是在核心方法里处理了呢？我们再看看 gopanic 的代码，如下：

```
func gopanic(e interface{}) {
    ...
    for {
        // defer...
        ...
        pc := d.pc
        sp := unsafe.Pointer(d.sp) // must be pointer so it gets adjusted during stack copy
        freedefer(d)

        // recover...
        **if p.recovered** {
            atomic.Xadd(&runningPanicDefers, -1)

            gp._panic = p.link
            for gp._panic != nil && gp._panic.aborted {
                gp._panic = gp._panic.link
            }
            if gp._panic == nil { 
                gp.sig = 0
            }

            gp.sigcode0 = uintptr(sp)
            gp.sigcode1 = pc
            mcall(recovery)
            throw("recovery failed") 
        }
    }
    ...
}
```

我们回到 gopanic 方法中再仔细看看，发现实际上是包含对 recover 流转的处理代码的。恢复流程如下：

- 判断当前 _panic 中的 recover 是否已标注为处理
- 从 _panic 链表中删除已标注中止的 panic 事件，也就是删除已经被恢复的 panic 事件
- 将相关需要恢复的栈帧信息传递给 recovery 方法的 gp 参数（每个栈帧对应着一个未运行完的函数。栈帧中保存了该函数的返回地址和局部变量）
- 执行 recovery 进行恢复动作
- 从流程来看，最核心的是 recovery 方法。它承担了异常流转控制的职责。代码如下：

```
func recovery(gp *g) {
 _// Info about defer passed in G struct._
 sp := gp.sigcode0
 pc := gp.sigcode1

 _// d's arguments need to be in the stack._
 if sp != 0 && (sp < gp.stack.lo || gp.stack.hi < sp) {
  print("recover: ", hex(sp), " not in [", hex(gp.stack.lo), ", ", hex(gp.stack.hi), "]\n")
  throw("bad recovery")
 }

 _// Make the deferproc for this d return again,_
 _// this time returning 1.  The calling function will_
 _// jump to the standard return epilogue._
 gp.sched.sp = sp
 gp.sched.pc = pc
 gp.sched.lr = 0
 gp.sched.ret = 1
 gogo(&gp.sched)
}
```

粗略一看，似乎就是很简单的设置了一些值？但实际上设置的是编译器中伪寄存器的值，常常被用于维护上下文等。在这里我们需要结合 gopanic 方法一同观察 recovery 方法。它所使用的栈指针 sp 和程序计数器 pc 是由当前 defer 在调用流程中的 deferproc 传递下来的，_因此实际上最后是通过 gogo 方法跳回了 deferproc 方法_。另外我们注意到：

`gp.sched.ret = 1`

在底层中程序将 gp.sched.ret 设置为了 1，也就是没有实际调用 deferproc 方法，直接修改了其返回值。意味着默认它已经处理完成。直接转移到 deferproc 方法的下一条指令去。至此为止，异常状态的流转控制就已经结束了。接下来就是继续走 defer 的流程了.

## **panic 抛出**

当然如果所有的 defer 都没有指明显式的 recover，那么这时候则直接在运行时抛出 panic 信息：

```
_// 消耗完所有的 defer 调用，保守地进行 panic_
_// 因为在冻结之后调用任意用户代码是不安全的，所以我们调用 preprintpanics 来调用_
_// 所有必要的 Error 和 String 方法来在 startpanic 之前准备 panic 字符串。_
preprintpanics(gp._panic)

fatalpanic(gp._panic) _// 不应该返回_
_(_int)(nil) = 0      _// 无法触及_
```

## recover 后同一函数又 panic

这部分可以参考幼鳞实验室

[https://mp.weixin.qq.com/s/vcJ6TsnknaCoYhH6XZnNMw](https://mp.weixin.qq.com/s/vcJ6TsnknaCoYhH6XZnNMw)

对于链表中已经被恢复的 panic，打印它的信息时会加上 recovered 标记，panic 链表每一项都输出后程序退出。

```python
panic:panicA[recovered]
panic:panicA2
```

同时包括 recover 之后恢复到哪里，recover 后恢复到哪里

## **总结**

从 panic 和 recover 这对关键字的实现上可以看出，可恢复的 panic 必须要 recover 的配合。而且，这个 recover 必须位于同一 goroutine 的直接调用链上（例如，如果 A 依次调用了 B 和 C，而 B 包含了 recover，而 C 发生了 panic，则这时 B 的 panic 无法恢复 C 的 panic；又例如 A 调用了 B 而 B 又调用了 C，那么 C 发生 panic 时，如果 A 要求了 recover 则仍然可以恢复）， 否则无法对 panic 进行恢复。

当一个 panic 被恢复后，调度并因此中断，会重新进入调度循环，进而继续执行 recover 后面的代码， 包括比 recover 更早的 defer（因为已经执行过得 defer 已经被释放，而尚未执行的 defer 仍在 goroutine 的 defer 链表中）， 或者 recover 所在函数的调用方。

# 参考

## 【Golang】图解 panic & recover

[https://mp.weixin.qq.com/s/vcJ6TsnknaCoYhH6XZnNMw](https://mp.weixin.qq.com/s/vcJ6TsnknaCoYhH6XZnNMw)

## Golang panic 和 recover 实现原理（强推）

> [https://mp.weixin.qq.com/s/ZmfwNlq5_A2RgpUSkJQXrQ](https://mp.weixin.qq.com/s/ZmfwNlq5_A2RgpUSkJQXrQ)

## 附录 B：Goroutine 与 panic、recover 的小问题

[https://golang2.eddycjy.com/posts/appendix/02-goroutine-panic/](https://golang2.eddycjy.com/posts/appendix/02-goroutine-panic/)

# 面试题整理

## **为什么 recover 一定要放在 defer 才生效？**

当一个 `panic` 发生时，Go 运行时会开始执行当前 `goroutine` 中注册的所有 `defer` 函数。这是 `panic` 恢复的唯一机会。

因为 _panic.recovered 字段的的修改时机，只能在 for 循环内的第三步执行 _defer 延迟函数。

在 Go 的运行时中，每个 `goroutine` 都有一个 `_panic` 链表，用于存储当前的 `panic` 状态。`recover` 函数实际上是检查这个链表并尝试恢复 `panic` 的过程。

## **为什么 recover 只能当前协程有效？**

在 gopanic 里，只遍历执行当前 goroutine 上的 _defer 函数链条。所以，如果挂在其他 goroutine 的 defer 函数做了 recover ，那么没有丝毫用途。

```python
_//获取当前goroutinue上挂的defer_    
   d := gp._defer    
   _// 步骤：执行 defer 函数_    
   reflectcall(nil, unsafe.Pointer(d.fn), deferArgs(d), uint32(d.siz), uint32(d.siz))    
   _// 步骤：执行完成，把这个 defer 从链表里摘掉；_    
   gp._defer = d.link
```

## recover 能捕获所有错误吗？

不能！

[Go 有哪些无法恢复的致命场景？](https://mp.weixin.qq.com/s?__biz=MzI2MzEwNTY3OQ==&mid=2648984202&idx=1&sn=6a24b99fb3c7f1d0c1a2790cca956b77&scene=21#wechat_redirect)

像

- 并发读写 map `fatal error: concurrent map read and map write`
- 堆栈内存耗尽(如递归)

```
runtime: goroutine stack exceeds 1000000000-**byte** limit
runtime: sp=0xc0200e1bf0 stack=[0xc0200e0000, 0xc0400e0000]
fatal error: stack overflow
```

- 将 nil 函数作为 goroutine 启动 `fatal error: go of nil func value`
- goroutines 死锁  `fatal error: all goroutines are asleep - deadlock!`
- 线程超过设置的最大限制  `fatal error: thread exhaustion`
- 超出可用内存 `fatal error: runtime: out of memory`

总之 都会报 **fatal error:xxxxxxxx**

## 面试题 3：子协程 `panic` 对主协程的影响

- **问题**：如果一个子协程中发生了 `panic`，这是否会影响主协程中 `defer` 的执行？
- **答案**：是的，如果子协程中的 `panic` 没有被捕获，它会中断子协程并冒泡到主协程。如果主协程中没有 recover 调用捕获这个 `panic`，那么程序将终止，导致主协程中的 `defer` 可能不会被执行。如果使用了 `os.Exit(1)`，那么所有的 `defer` 都将不会执行。

```python
package main

import (
        "fmt"
        "time"
)

func main() {
        defer fmt.Println("main defer executed")

        go func() {
                defer fmt.Println("goroutine defer executed")
                fmt.Println("goroutine started")
                panic("goroutine panic")
        }()

        // Sleep to give the goroutine time to panic and execute its defer statement
        time.Sleep(1 * time.Second)

        fmt.Println("main function end")
}
```

输出结果：

```python
goroutine started
goroutine defer executed
panic: goroutine panic

goroutine 20 [running]:
main.main.func1()
        /tmp/sandbox1880328131/prog.go:14 +0xaa
created by main.main in goroutine 1
        /tmp/sandbox1880328131/prog.go:11 +0x6c

Program exited.
```

## caller 方法中的 recover,也可以恢复 callee 方法里的 panic

> [https://mp.weixin.qq.com/s/C3tt-KUKoDObRPFSU7RpAg](https://mp.weixin.qq.com/s/C3tt-KUKoDObRPFSU7RpAg)

因为他们是同一个 goroutine 啊

# Go 语言 `panic` 机制面试题及答案

[https://mp.weixin.qq.com/s/byouCtNulnjYDluDaO9wIw](https://mp.weixin.qq.com/s/byouCtNulnjYDluDaO9wIw)

## 面试题 1：`panic` 的执行流程是怎样的？

- **答案**：

`panic` 会停掉当前正在执行的程序，包括所有协程。它比 `exit` 更有秩序，会先处理完当前 `goroutine` 已经 `defer` 挂上去的任务，然后退出整个程序。底层实现中，`panic` 会通过 `gopanic` 函数来执行，该函数遍历当前 `goroutine` 的 `defer` 链表，尝试执行 `defer` 函数，并检查是否有 `recover` 调用。

## 面试题 2：`panic` 结构是怎样的？

- **答案**：
  ```go
  ```

type _panic struct {
argp      unsafe.Pointer  // 指向 defer 调用的参数的指针
arg       interface{}     // panic 传入的参数
link      *_panic         // 指向上一个调用的_panic，形成链表结构
recovered bool            // 是否已被 recover 恢复
aborted   bool            // panic 是否被强行中止
}

```
	`_panic`结构体包含`argp`（指向`defer`调用参数的指针）、`arg`（`panic`传入的参数）、`link`（形成链表，指向上一个`_panic`）、`recovered`（是否被`recover`恢复）和`aborted`（`panic`是否被强行中止）。

## 面试题3：`recover`为什么只能在`defer`中生效？

- **答案**：

`recover`只能在`defer`中生效，因为`_panic.recovered`字段的修改时机只能在`gopanic`函数的`for`循环内执行`_defer`延迟函数时发生。`recover`调用会检查`_panic`结构体，如果发现`recovered`为`false`，则将其设置为`true`，表示`panic`已被恢复。



## 面试题4：`recover`为什么只能对当前协程有效？

- **答案**：

`recover`只能对当前协程有效，因为在`gopanic`函数中，只遍历执行当前`goroutine`上的`_defer`函数链条。如果`recover`挂在其他`goroutine`的`defer`函数上，则不会有任何效果。



## 面试题5：`panic`和`defer`如何相互配合工作？

- **答案**：

当`panic`发生时，`gopanic`函数会遍历当前`goroutine`的`defer`链表。对于每个`defer`，会检查其`started`状态和`_panic`字段。如果`defer`尚未执行（`started`为`false`），并且没有关联的`panic`（或关联的`panic`已被恢复），则执行该`defer`。如果在执行`defer`过程中发生`recover`调用，则会停止`panic`的传播，并从`defer`中恢复。



## 总结

- `panic`在Go语言中用于异常处理，它会中断程序的执行。

- `panic`会触发当前`goroutine`中的`defer`函数执行，直到所有`defer`执行完毕或遇到`recover`。

- `recover`用于恢复`panic`，只能在`defer`中调用，并且只能恢复当前`goroutine`中的`panic`。



```
