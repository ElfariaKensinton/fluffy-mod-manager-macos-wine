/* Exercise the actual patched scanner in a mapped stock Fluffy executable.
 * No game, mods, or save files are touched. Compile with MinGW, run in Wine. */
#define UNICODE
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
static SIZE_T largest_allocation, largest_read;
static LPVOID WINAPI tracked_alloc(LPVOID p, SIZE_T n, DWORD kind, DWORD protect) {
    if (n > largest_allocation) largest_allocation = n;
    return VirtualAlloc(p,n,kind,protect);
}
static BOOL WINAPI tracked_read(HANDLE p,LPCVOID a,LPVOID b,SIZE_T n,SIZE_T *read) {
    if (n > largest_read) largest_read = n;
    return ReadProcessMemory(p,a,b,n,read);
}
static void check(int ok,const char *message) {
    if (!ok) { fprintf(stderr,"FAIL: %s (error %lu)\n",message,GetLastError()); exit(1); }
}
int wmain(int argc,wchar_t **argv) {
    check(argc==5,"arguments: EXE scanner-rva handle-rva base-rva");
    BYTE *image=(BYTE*)LoadLibraryExW(argv[1],NULL,DONT_RESOLVE_DLL_REFERENCES);
    check(image!=NULL,"map patched executable");
    IMAGE_NT_HEADERS64 *nt=(void*)(image+((IMAGE_DOS_HEADER*)image)->e_lfanew);
    IMAGE_IMPORT_DESCRIPTOR *d=(void*)(image+nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress);
    for (;d->Name;d++) {
        IMAGE_THUNK_DATA64 *names=(void*)(image+(d->OriginalFirstThunk?d->OriginalFirstThunk:d->FirstThunk));
        IMAGE_THUNK_DATA64 *slots=(void*)(image+d->FirstThunk);
        for (;names->u1.AddressOfData;names++,slots++) {
            if (IMAGE_SNAP_BY_ORDINAL64(names->u1.Ordinal)) continue;
            char *name=(char*)((IMAGE_IMPORT_BY_NAME*)(image+names->u1.AddressOfData))->Name;
            void *fn=NULL;
            if (!strcmp(name,"VirtualAlloc")) fn=tracked_alloc;
            if (!strcmp(name,"VirtualFree")) fn=VirtualFree;
            if (!strcmp(name,"VirtualQueryEx")) fn=VirtualQueryEx;
            if (!strcmp(name,"ReadProcessMemory")) fn=tracked_read;
            if (fn) {DWORD old;check(VirtualProtect(slots,sizeof(*slots),PAGE_READWRITE,&old),"unprotect IAT");slots->u1.Function=(uintptr_t)fn;VirtualProtect(slots,sizeof(*slots),old,&old);}
        }
    }
    uintptr_t (*scan)(const char*,int,void*,int)=(void*)(image+wcstoul(argv[2],NULL,16));
    HANDLE *handle=(void*)(image+wcstoul(argv[3],NULL,16));
    BYTE **base=(void*)(image+wcstoul(argv[4],NULL,16));
    *handle=GetCurrentProcess();
    BYTE *zone=VirtualAlloc(NULL,0x56000000,MEM_RESERVE,PAGE_NOACCESS);
    check(zone!=NULL,"reserve sparse address range");*base=zone;
    BYTE *region=VirtualAlloc(zone+65536,2*1048576,MEM_COMMIT,PAGE_READWRITE);
    check(region!=NULL,"commit fixture pages");
    const char pat[]="QwErTyUi";SIZE_T n=sizeof(pat)-1;
    BYTE *first=region+1048576-3,*second=region+1048576+8192,*last=region+2*1048576-n;
    memcpy(first,pat,n);memcpy(second,pat,n);memcpy(last,pat,n);
    check(scan(pat,n,NULL,-1)==(uintptr_t)first,"pattern crossing chunk boundary");
    check(scan(pat,n,NULL,2)==(uintptr_t)second,"second occurrence");
    check(scan(pat,n,NULL,3)==(uintptr_t)last,"last legal pattern position");
    check(scan("Qw?rTyUi",n,NULL,-1)==(uintptr_t)first,"wildcard matching");
    check(scan("absent!!",8,NULL,-1)==0,"absent pattern across reserved gaps");
    check(scan(pat,0,NULL,-1)==0,"reject empty pattern");
    check(scan(pat,65537,NULL,-1)==0,"reject excessive pattern length");
    BYTE *guard=VirtualAlloc(zone+4*1048576,4096,MEM_COMMIT,PAGE_READWRITE|PAGE_GUARD);
    check(guard!=NULL,"create guard page");
    check(scan("absent!!",8,NULL,-1)==0,"skip guarded pages");
    MEMORY_BASIC_INFORMATION mbi;VirtualQuery(guard,&mbi,sizeof(mbi));
    check((mbi.Protect&PAGE_GUARD)!=0,"guard protection preserved");
    VirtualFree(zone,0,MEM_RELEASE);
    zone=VirtualAlloc(NULL,0x56000000,MEM_RESERVE,PAGE_NOACCESS);check(zone!=NULL,"reserve large fixture");*base=zone;
    region=VirtualAlloc(zone+65536,0x11000000,MEM_COMMIT,PAGE_READWRITE);check(region!=NULL,"commit region larger than 256 MiB");
    memcpy(region,pat,n);
    check(scan(pat,n,NULL,-1)==(uintptr_t)region,"large-region match at offset zero");
    check(largest_allocation<=1048576&&largest_read<=1048576,"bounded allocation and reads");
    VirtualFree(zone,0,MEM_RELEASE);FreeLibrary((HMODULE)image);
    printf("PASS: real patched scanner; boundary, nth, wildcard, final-byte, sparse, guard, invalid-input and >256 MiB tests; max allocation/read %llu/%llu bytes\n",(unsigned long long)largest_allocation,(unsigned long long)largest_read);
    return 0;
}
