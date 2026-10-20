#define UNICODE
#define _UNICODE
#include <windows.h>
#include <wchar.h>
#include <stdlib.h>
#include <string.h>

static void fail(const wchar_t *message) {
    MessageBoxW(NULL, message, L"Fluffy Mod Manager launcher", MB_OK | MB_ICONERROR);
}

static BOOL set_opengl_override(void) {
    HKEY key;
    const wchar_t *subkey = L"Software\\Wine\\AppDefaults\\Modmanager.exe\\DllOverrides";
    const wchar_t *value = L"native,builtin";
    LONG status = RegCreateKeyExW(HKEY_CURRENT_USER, subkey, 0, NULL, 0,
                                  KEY_SET_VALUE, NULL, &key, NULL);
    if (status != ERROR_SUCCESS) return FALSE;
    status = RegSetValueExW(key, L"opengl32", 0, REG_SZ,
                            (const BYTE *)value,
                            (DWORD)((wcslen(value) + 1) * sizeof(wchar_t)));
    RegCloseKey(key);
    return status == ERROR_SUCCESS;
}

static wchar_t *make_environment(void) {
    LPWCH old = GetEnvironmentStringsW();
    if (!old) return NULL;
    SIZE_T capacity = 32768, used = 0;
    wchar_t *block = (wchar_t *)calloc(capacity, sizeof(wchar_t));
    if (!block) { FreeEnvironmentStringsW(old); return NULL; }
    const wchar_t *vars[] = { L"WINEDLLOVERRIDES=opengl32=native,builtin", L"GALLIUM_DRIVER=llvmpipe" };
    const size_t keys[] = { 16, 14 };
    for (LPWCH p = old; *p; p += wcslen(p) + 1) {
        BOOL replace = FALSE;
        for (int i = 0; i < 2; ++i)
            if (_wcsnicmp(p, vars[i], keys[i]) == 0 && p[keys[i]] == L'=') replace = TRUE;
        if (!replace) {
            size_t n = wcslen(p) + 1;
            if (used + n + 128 >= capacity) { free(block); FreeEnvironmentStringsW(old); return NULL; }
            memcpy(block + used, p, n * sizeof(wchar_t)); used += n;
        }
    }
    FreeEnvironmentStringsW(old);
    for (int i = 0; i < 2; ++i) {
        size_t n = wcslen(vars[i]) + 1;
        memcpy(block + used, vars[i], n * sizeof(wchar_t)); used += n;
    }
    block[used] = L'\0';
    return block;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR command_line, int show) {
    (void)instance; (void)previous; (void)command_line; (void)show;
    if (!set_opengl_override()) {
        fail(L"Could not set the Wine opengl32 override for Modmanager.exe.");
        return 1;
    }
    wchar_t folder[MAX_PATH];
    DWORD n = GetModuleFileNameW(NULL, folder, MAX_PATH);
    if (!n || n >= MAX_PATH) { fail(L"Could not determine the launcher folder."); return 1; }
    wchar_t *slash = wcsrchr(folder, L'\\');
    if (!slash) { fail(L"Could not determine the launcher folder."); return 1; }
    slash[1] = L'\0';
    wchar_t exe[MAX_PATH * 2];
    if (swprintf(exe, sizeof(exe) / sizeof(exe[0]), L"%lsModmanager.exe", folder) < 0 || GetFileAttributesW(exe) == INVALID_FILE_ATTRIBUTES) {
        fail(L"Modmanager.exe was not found beside this launcher. Keep the launcher in the Fluffy Mod Manager folder."); return 1;
    }
    wchar_t *env = make_environment();
    if (!env) { fail(L"Could not prepare the Wine environment."); return 1; }
    STARTUPINFOW si = {0}; si.cb = sizeof(si);
    PROCESS_INFORMATION pi = {0};
    BOOL ok = CreateProcessW(exe, NULL, NULL, NULL, FALSE, CREATE_UNICODE_ENVIRONMENT, env, folder, &si, &pi);
    free(env);
    if (!ok) { fail(L"Could not start Modmanager.exe. Check that it is present and can run in this Wine prefix."); return 1; }
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    return 0;
}
