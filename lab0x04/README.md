# `CreateThread`
## 实验过程
### 完整代码
```cpp
#include <windows.h>
#include <tchar.h>
#include <strsafe.h>

#define MAX_THREADS 10	//创建线程数
#define BUF_SIZE 255

DWORD WINAPI MyThreadFunction(LPVOID lpParam);
void ErrorHandler(LPTSTR lpszFunction);

// Sample custom data structure for threads to use.
// This is passed by void pointer so it can be any data type
// that can be passed using a single void pointer (LPVOID).
typedef struct MyData {
    int val1;
    int val2;
} MYDATA, * PMYDATA;

//支持unicode, main的别名
int _tmain()
{
    PMYDATA pDataArray[MAX_THREADS];
    DWORD   dwThreadIdArray[MAX_THREADS];
    HANDLE  hThreadArray[MAX_THREADS];

    // Create MAX_THREADS worker threads.

    DWORD start = GetTickCount();
    //The return value is the number of milliseconds that have elapsed since the system was started.

    for (int i = 0; i < MAX_THREADS; i++)
    {
        // Allocate memory for thread data.
        pDataArray[i] = (PMYDATA)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
            sizeof(MYDATA));

        if (pDataArray[i] == NULL)
        {
            // If the array allocation fails, the system is out of memory
            // so there is no point in trying to print an error message.
            // Just terminate execution.
            ExitProcess(2);
        }

        // Generate unique data for each thread to work with.

        pDataArray[i]->val1 = i;
        pDataArray[i]->val2 = i + 100;

        // Create the thread to begin execution on its own.

        hThreadArray[i] = CreateThread(
            NULL,                   // default security attributes
            0,                      // use default stack size
            MyThreadFunction,       // thread function name
            pDataArray[i],          // argument to thread function 
            0,                      // use default creation flags 
            &dwThreadIdArray[i]);   // returns the thread identifier 
        // MyThreadFunction(pDataArray[i]);

        // Check the return value for success.
        // If CreateThread fails, terminate execution. 
        // This will automatically clean up threads and memory. 

        if (hThreadArray[i] == NULL)
        {
            // ErrorHandler(TEXT("CreateThread"));
            printf("CreateThread Error(%d)", GetLastError());
            ExitProcess(3);
        }
    } // End of main thread creation loop.

    // Wait until all threads have terminated.
    // TRUE表示所有都要执行完毕才返回, FALSE只要有任意一个执行完毕就返回
    // INFINTE 无限等待
    WaitForMultipleObjects(MAX_THREADS, hThreadArray, TRUE, INFINITE);

    DWORD end = GetTickCount();
    printf("Tick count: %d\n", end - start);

    // Close all thread handles and free memory allocations.

    for (int i = 0; i < MAX_THREADS; i++)
    {
        CloseHandle(hThreadArray[i]);
        if (pDataArray[i] != NULL)
        {
            HeapFree(GetProcessHeap(), 0, pDataArray[i]);
            pDataArray[i] = NULL;    // Ensure address is not reused.
        }
    }
    return 0;
}

DWORD WINAPI MyThreadFunction(LPVOID lpParam)
{
    PMYDATA pDataArray;
    pDataArray = (PMYDATA)lpParam;
    Sleep(1000);
    //人为加长时间, 使实验观察结果更明显
    // Print the parameter values using thread-safe functions.
    printf("Parameters = %d, %d\n", pDataArray->val1, pDataArray->val2);
    return 0;
}

void ErrorHandler(LPTSTR lpszFunction)
{
    // Retrieve the system error message for the last-error code.

    LPVOID lpMsgBuf;
    LPVOID lpDisplayBuf;
    DWORD dw = GetLastError();

    FormatMessage(
        FORMAT_MESSAGE_ALLOCATE_BUFFER |
        FORMAT_MESSAGE_FROM_SYSTEM |
        FORMAT_MESSAGE_IGNORE_INSERTS,
        NULL,
        dw,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        (LPTSTR)&lpMsgBuf,
        0, NULL);

    // Display the error message.

    lpDisplayBuf = (LPVOID)LocalAlloc(LMEM_ZEROINIT,
        (lstrlen((LPCTSTR)lpMsgBuf) + lstrlen((LPCTSTR)lpszFunction) + 40) * sizeof(TCHAR));
    StringCchPrintf((LPTSTR)lpDisplayBuf,
        LocalSize(lpDisplayBuf) / sizeof(TCHAR),
        TEXT("%s failed with error %d: %s"),
        lpszFunction, dw, lpMsgBuf);
    MessageBox(NULL, (LPCTSTR)lpDisplayBuf, TEXT("Error"), MB_OK);

    // Free error-handling buffer allocations.

    LocalFree(lpMsgBuf);
    LocalFree(lpDisplayBuf);
}
```
### 并发执行, 多线程
  直接运行上方代码, 可得以下结果: <br>
  ![并发执行](img/multi-thread.jpg)
### 串行执行, 单线程
- 注释以下代码<br>
    ```cpp
    hThreadArray[i] = CreateThread(
    NULL,                   // default security attributes
    0,                      // use default stack size
    MyThreadFunction,       // thread function name
    pDataArray[i],          // argument to thread function 
    0,                      // use default creation flags 
    &dwThreadIdArray[i]);   // returns the thread identifier

    if (hThreadArray[i] == NULL)
    {
        // ErrorHandler(TEXT("CreateThread"));
        printf("CreateThread Error(%d)", GetLastError());
        ExitProcess(3);
    }

	CloseHandle(hThreadArray[i]);
    ```
- 解除`MyThreadFunction(pDataArray[i]);`的注释, 然后编译运行代码, 可得以下结果: <br>
  ![串行执行](img/single-thread.jpg)
## 实验总结
- 每个线程里`Sleep(1000)`花费的时间占主要部分, `printf`花费的时间可以忽略不计, 因此每个线程执行完毕需要`1000 tick count`
- 在第一次执行中总共也只花费了1000多一点的时间, 并且从打印结果可以看到, 各线程执行完毕的顺序与开始执行的顺序不同, 说明这些进程是并发执行的, 执行完毕与开始执行顺序不同是由并发导致的
- 第二次执行所花费的时间约为1000的十倍, 并且各线程执行完毕的顺序与开始执行的顺序相同, 说明这些进程是串行执行的
# `CreateProcess`
## 实验过程
### 完整代码
```cpp
#include <windows.h>
#include <stdio.h>
#include <tchar.h>

void _tmain( int argc, TCHAR *argv[] )
{
    STARTUPINFO si;
    PROCESS_INFORMATION pi;

    ZeroMemory( &si, sizeof(si) );
    si.cb = sizeof(si);
    ZeroMemory( &pi, sizeof(pi) );

    if( argc != 2 )
    {
        printf("Usage: %s [cmdline]\n", argv[0]);
        return;
    }

    // Start the child process. 
    if( !CreateProcess( NULL,   // No module name (use command line)
        argv[1],        // Command line
        NULL,           // Process handle not inheritable
        NULL,           // Thread handle not inheritable
        FALSE,          // Set handle inheritance to FALSE
        0,              // No creation flags
        NULL,           // Use parent's environment block
        NULL,           // Use parent's starting directory 
        &si,            // Pointer to STARTUPINFO structure
        &pi )           // Pointer to PROCESS_INFORMATION structure
    ) 
    {
        printf( "CreateProcess failed (%d).\n", GetLastError() );
        return;
    }

    // Wait until child process exits.
    WaitForSingleObject( pi.hProcess, INFINITE );

    // Close process and thread handles.
    CloseHandle( pi.hProcess );
    CloseHandle( pi.hThread );
}
```
### 创建进程与观察
- 使用命令行运行代码, 用`CreateProcess`调用记事本, 使用`ProcessExplorer`可以查看进程的父子关系<br>
  ![使用方法-父子进程](img/createprocess-usage.jpg)
- 还可以进行递归调用: <br>
  ![递归调用](img/recursion.jpg)
## 实验总结
- `cmd`中引号嵌套可以使用`\`进行转义, 目前最多只能嵌套两层引号, 如: <br>
  `createprocess.exe "createprocess.exe \"createprocess.exe notepad.exe\""`
- 进程之间存在父子关系, 调用的进程是父进程, 被调用的为子进程