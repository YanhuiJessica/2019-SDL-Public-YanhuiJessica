# `WinDbg`的使用

## 实验要求

- 修改 Win7 下的计算器的显示过程，使得当你输入的内容是特定数字如 "999" 的时候通过调试器脚本自动改为 "666"

## 实验过程

### 脚本

- 使用`dd`查看，最终确定显示的数字存储在`ebp`
  - 因机而异，有的是在`poi(esp+8)`

- `command.txt`
```
as /mu content ebp
.block{.if($scmp("${content}","999")==0){ezu ebp "666";}.else{.echo content}}
g
```

### 操作步骤

- 打开`calc`，在`WinDbg`的`File`选择`Attach to a Process`
  - 如果选择`OpenExecutable`，那么在`calc`启动时会触发多次`SetWindowTextW`
- 下断点：`bu user32!SetWindowTextW "$><C:\\Users\\yanhui\\Desktop\\command.txt"`并`g`
- 输入`999`成功变为`666`

### 操作演示

- [WinDbg操作演示](https://pan.baidu.com/s/14cvNvIeFjtsTGceFtvd4Ww)

## 实验总结

- 当发现显示异常时，可以考虑是否是编码的问题