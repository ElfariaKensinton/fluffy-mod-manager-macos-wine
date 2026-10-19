.intel_syntax noprefix
.text
.global trainer_scan
trainer_scan:
    # Preserve Fluffy's exact prologue and existing x64 unwind description.
    .byte 0x48, 0x8b, 0xc4 # mov rax, rsp; preserve MSVC encoding
    mov [rax+8], rbx
    mov [rax+16], rbp
    mov [rax+32], rsi
    push rdi
    push r12
    push r13
    push r14
    push r15
    sub rsp, 0xb0
    mov rdi, rcx
    movsxd r15, edx
    mov r13d, r9d
    xor r14d, r14d
    lea eax, [rdx-1]
    cmp eax, 65535
    ja early_fail
    mov r12, QWORD PTR fluffy_gamehandle[rip]
    mov rbp, QWORD PTR fluffy_gamebase[rip]
    lea rax, [rbp+0x5525c000]
    mov [rsp+0x48], rax
    xor ecx, ecx
    mov edx, 1048576
    mov r8d, 0x3000
    mov r9d, 4
    call QWORD PTR __imp_VirtualAlloc[rip]
    test rax, rax
    jz early_fail
    mov [rsp+0x38], rax
query:
    mov rcx, r12
    mov rdx, rbp
    lea r8, [rsp+0x50]
    mov r9d, 48
    call QWORD PTR __imp_VirtualQueryEx[rip]
    test rax, rax
    jz failed
    mov rax, [rsp+0x50]
    add rax, [rsp+0x68]
    cmp rax, [rsp+0x48]
    cmova rax, [rsp+0x48]
    mov [rsp+0x40], rax
    cmp DWORD PTR [rsp+0x70], 0x1000
    jne skip_region
    test DWORD PTR [rsp+0x74], 0x101
    jnz skip_region
    mov rsi, rax
    sub rsi, rbp
    mov eax, 1048576
    cmp rsi, rax
    cmova rsi, rax
    cmp rsi, r15
    jb skip_region
    lea rax, [rbp+rsi]
    cmp rax, [rsp+0x40]
    je next_ready
    sub rax, r15
    inc rax
next_ready:
    mov [rsp+0x28], rax
    mov QWORD PTR [rsp+0x30], 0
    lea rax, [rsp+0x30]
    mov [rsp+0x20], rax
    mov rcx, r12
    mov rdx, rbp
    mov r8, [rsp+0x38]
    mov r9, rsi
    call QWORD PTR __imp_ReadProcessMemory[rip]
    mov rsi, [rsp+0x30]
    cmp rsi, r15
    jb advance
    sub rsi, r15
    mov r10, [rsp+0x38]
    xor ebx, ebx
candidate:
    xor ecx, ecx
compare:
    mov al, [rdi+rcx]
    cmp al, '?'
    je character_ok
    lea rdx, [r10+rbx]
    cmp al, [rdx+rcx]
    jne next_candidate
character_ok:
    inc rcx
    cmp rcx, r15
    jb compare
    inc r14d
    cmp r13d, -1
    je matched
    cmp r13d, r14d
    je matched
next_candidate:
    inc rbx
    cmp rbx, rsi
    jbe candidate
advance:
    mov rbp, [rsp+0x28]
    jmp continue_scan
skip_region:
    mov rbp, [rsp+0x40]
continue_scan:
    cmp rbp, [rsp+0x48]
    jb query
failed:
    xor edi, edi
    jmp release
matched:
    lea rdi, [rbp+rbx]
release:
    mov rcx, [rsp+0x38]
    xor edx, edx
    mov r8d, 0x8000
    call QWORD PTR __imp_VirtualFree[rip]
    mov rax, rdi
    jmp epilogue
early_fail:
    xor eax, eax
epilogue:
    lea r11, [rsp+0xb0]
    mov rbx, [r11+0x30]
    mov rbp, [r11+0x38]
    mov rsi, [r11+0x48]
    mov rsp, r11
    pop r15
    pop r14
    pop r13
    pop r12
    pop rdi
    ret
.global trainer_scan_end
trainer_scan_end:
