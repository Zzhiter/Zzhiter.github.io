---
authors: Zzhiter
categories: [Git]
---
> 终于结合具体的使用场景和自己的使用体验，把这三者的特点和差别总结出来了，太爽了！

# 一、git merge

## 1.使用

- 将分支切换到 master 上去：git checkout master
- 将分支 feature 合并到当前分支（即 master 分支）上：git merge feature

![](/images/VVmwbXbsBo3S4pxcLbtcq28rn2d.png)

## 2.特点

- 只处理一次冲突
- 引入了一次合并的历史记录，合并后的所有 commit 会按照提交时间从旧到新排列
- 所有的过程信息更多，可能会提高之后查找问题的难度

# 二、git rebase

## 1.使用

与 git merge 一致，git rebase 的目的也是将一个分支的更改并入到另外一个分支中去。

![](/images/QNGQbalNeoqwJPxoJpucy10Bnxh.png)

- 执行 git rebase master 的操作，意味着让当前分支 feature 相对于 分支 master 进行变基
- 遇到冲突，进行对比的双方分别是 master 分支的最新内容和 feature 分支的第一次提交的内容。
- 在我们解决了冲突之后，需要执行 git rebase --continue 来继续变基的操作。
- 执行之后又遇到了冲突，这次是与 feature 分支的第二次提交进行对比出现的冲突，意味着我们需要多次解决同一个地方的冲突。

## 2.特点

- 改变当前分支从 master 上拉出分支的位置
- 没有多余的合并历史的记录，且合并后的 commit 顺序不一定按照 commit 的提交时间排列
- 可能会多次解决同一个地方的冲突（有 squash 来解决）
- 更清爽一些，master 分支上每个 commit 点都是相对独立完整的功能单元

## 3.交互模式

```css
git rebase -i HEAD~4
```

指定了对当前分支的最近四次提交进行操作。

![](/images/YnD3bhCvEoVW32xUUlOcAszonUd.png)

中间红框内有一些命令，可以用来处理某次提交的，可以使用 squash 来将所有的 commit 合并成一次提交，编辑并保存之后会出现编辑提交的信息的提示，编辑提交即可。

## 4.git rebase 和 git merge 的区别

- **rebase 会把你当前分支的 commit 放到公共分支的最后面,所以叫变基。就好像你从公共分支又重新拉出来这个分支一样。**
- **而 merge 会把公共分支和你当前的 commit 合并在一起，形成一个新的 commit 提交**

**优劣：**

- git merge 优点是分支代码合并后不破坏原分支代码的提交记录，缺点是会产生额外的提交记录并进行两条分支的合并
- git rebase 优点是可以将对象分支的提交记录续道目标分支上，形成线性提交历史记录，review 时更加直观

## 5.什么时候使用 rebase

- 不能在一个共享的分支上进行 git rebase 操作
  - 因为往后放的这些 commit 都是新的,这样其他从这个公共分支拉出去的人，都需要再重新 merge，导致提交记录混乱

如下图：

![](/images/IFNibJUuuoR6jhxpqfpcci9cnJe.png)

![](/images/F3uMbJXrcoeeVvxblUecNq9onph.png)

> 上面这张图，无敌
> 核心就是，你无法保证你当前所在的这个 feature 分支，从 master 分支 checkout 新建分支出来之后，master 分支不会再有新的 commit D’了。
> 如果有了新的 commit：
>
> 1. 要么你就在 feature 分支，rebase master，把 feature 分支的基 Base 更新到 commit D’之后，这个时候如果 master 分支有多个新的 commit，你就需要一个个 rebase（可能多次解决冲突），这是正确解法。
> 2. 要么就把 feature 分支合并到 master，基于 commit D’创建一个新的 commit，即图中的 M，这是图中的错误的解法

> 下面这个其实说的有问题：
> 一个 feature 分支的项目因为误用 rebase 产生的后果。如果团队中的每个人都对公共分支进行 rebase 操作，那么后果就是乱成一片。
> 因此，尽量不要在一个共享的分支上进行 Git rebase 操作,避免出现项目分支代码提交记录错乱。

### 总结

- 合代码到公共分支上时用 git merge
- 合代码到个人分支时用 git rebase，形成线性提交历史记录

## Rebase 和 Merge 小比较

### Merge

- **用途**: 将一个分支的所有更改合并到另一个分支，通常用在将功能分支合并回主分支（如 `master` 或 `main`）时。
- **特点**: 会创建一个新的合并提交（merge commit），保留了两个分支的完整历史记录。

### Rebase

- **用途**: 将当前分支的起点移动到另一个分支的最新提交上。通常在你已经开始进行开发，而其他开发者也对主分支进行了更新时，使用 `rebase` 可以将你的更改基于主分支的最新状态。
- **特点**: 重新应用当前分支的提交在另一个分支的最新提交之后，从而使历史记录更为线性。

### Squashing

- **用途**: 将多个提交合并成一个提交，通常用于清理历史记录，使得提交记录更加简洁。可以在 `merge` 或 `rebase` 时使用 `--squash` 选项来进行。
- **特点**: 在 `merge` 时，通常称为 squash-merge；在 `rebase` 时，称为 squash-rebase。

### Pull Requests

- **用途**: 在使用 Git 托管服务（如 GitHub、GitLab、Bitbucket）时，可以配置如何处理 Pull Request（PR）。这些服务的界面可能会显示一个“Merge”按钮，但实际操作可以是 `merge`、`rebase`、`squash` 等多种方式。
- **特点**: 提供了灵活的选项来处理分支的合并方式，可以根据团队的工作流程来选择合适的方法。

总的来说，`merge` 更适合保留完整的历史记录，而 `rebase` 更适合保持历史记录的线性。如果你在处理个人分支或准备合并功能分支时，使用 `rebase` 可以让提交历史更为干净；而在合并到主分支时，`merge` 通常更为常见，尤其是当你希望保留完整的开发历史时。

# 三、git cherry-pick

## 1.基本使用

- git cherry-pick 的使用场景就是将一个分支中的部分的提交合并到其他分支

```xml
git checkout master 
git cherry-pick <commitHash>
```

使用以上命令以后，这个提交将会处在 master 的最前面

## 2.合并多个提交

```css
git cherry-pick <hashA> <hashB>     // 合并两个提交
git cherry-pick <hashA>..<hashB>    // 合并从A到B两个提交中到所有提交，但不包含A
git cherry-pick <hashA>^..<hashB>   // 合并从A到B两个提交中到所有提交，包含A
```

## 3.pick 以后产生了冲突

当执行了 cherry-pick 命令如果有冲突，就会报冲突错误

```scss
git cherry-pick --continue  // 1. 解决完冲突以后，继续下一个 cherry-pick
git cherry-pick --abort   // 2. 如果不想解决冲突，要放弃合并，用此命令回到操作以前
git cherry-pick --quit   // 3. 不想解决冲突，放弃合并，且保持现有情况，不回到操作以前
```

## 4.转移到另一个代码库

```c
git remote add target git://gitUrl //添加一个远程仓库target
git fetch target                   //远程代码抓取到本地
git log target/master              //获取该提交的哈希值
```

## 5.应用场景

想要合并某些内容，但又不想包含整个分支。这时用 cherry-pick 来合并单次提交。

比如：

现在你在基于 FeatA，FeatB 有了新的 commit（添加了一个 SDK），FeatA 和 FeatB 是完全并列的关系，这个时候你也想在 FeatA 上用这个 SDK，那你就可以把 FeatB 中关于添加 SDK 的这个 commit 改动摘过来。

```python
### `git cherry-pick`  
   
`git cherry-pick` 命令用于将一个或多个特定的提交（commit）从一个分支复制到另一个分支。它的主要用途是选择性地引入变更，而不需要合并整个分支。  
   
#### 用法示例：  
假设你在 `feature` 分支上有一个提交 `a1b2c3d`，你想把这个提交应用到 `main` 分支上。  
   
```sh  
git checkout main  
git cherry-pick a1b2c3d  
```

#### 主要特点：

- **选择性引入**：只引入指定的提交，而不是整个分支的历史。
- **冲突解决**：如果所选的提交与目标分支有冲突，需要手动解决冲突。
- **保持历史**：只复制指定的提交，不改变原始的提交历史。

```

### cherry-pick某个commit的时候，结果这个commit的改动，之前别人已经在你的分支的历史提交中应用了，所以相当于这次cherry-pick的改动就会为空。

这个时候，就会提示

```cpp
> git cherry-pick 23295e8b
On branch zhe/error_message
You are currently cherry-picking commit 23295e8.
  (all conflicts fixed: run "git cherry-pick --continue")
  (use "git cherry-pick --skip" to skip this patch)
  (use "git cherry-pick --abort" to cancel the cherry-pick operation)     

Untracked files:
  (use "git add <file>..." to include in what will be committed)
        .vscode/
        src/.idea/

nothing added to commit but untracked files present (use "git add" to track)
The previous cherry-pick is now empty, possibly due to conflict resolution.
If you wish to commit it anyway, use:

    git commit --allow-empty

Otherwise, please use 'git cherry-pick --skip'
```

这个时候，我们可以选择 git commit --allow-empty，或者直接放弃这次 cherry-pick 也行。因为你想要 cherry-pick 的 commit 的改动，你的分支已经实现了。

# 参考资料

[Git merge 和 rebase 分支合并命令的区别](https://juejin.cn/post/6844903603694469134)

[https://juejin.cn/post/703479306534...](https://juejin.cn/post/7034793065340796942)
