#Requires AutoHotkey v2.0
#SingleInstance Force

SetTitleMatchMode(2)

WorkflowWindowWatchDeadline := 0

PlacementDialogTitle(title)
{
    return (
        InStr(title, "1 / 2") ||
        InStr(title, "2 / 2") ||
        InStr(title, "1 / 4") ||
        InStr(title, "2 / 4") ||
        InStr(title, "3 / 4") ||
        InStr(title, "4 / 4")
    )
}

MoveFijiToolbarOnce()
{
    bestHwnd := 0
    for hwnd in WinGetList("ahk_class SunAwtFrame")
    {
        title := ""
        try title := WinGetTitle(hwnd)
        catch
            continue
        if InStr(title, "(Fiji Is Just) ImageJ") || InStr(title, "Fiji") || InStr(title, "ImageJ")
        {
            bestHwnd := hwnd
            break
        }
    }

    if !bestHwnd
    {
        for hwnd in WinGetList()
        {
            try className := WinGetClass(hwnd)
            catch
                continue
            if (className != "SunAwtFrame")
                continue
            try title := WinGetTitle(hwnd)
            catch
                continue
            if InStr(title, "(Fiji Is Just) ImageJ") || InStr(title, "Fiji") || InStr(title, "ImageJ")
            {
                bestHwnd := hwnd
                break
            }
        }
    }

    if !bestHwnd
        return

    try
    {
        WinGetPos(, , &w, &h, bestHwnd)
        MonitorGetWorkArea(1, &left, &top, &right, &bottom)
        x := Max(left, right - w - 10)
        WinMove(x, top + 10, , , bestHwnd)
    }
}

HideFijiLauncherOverlayWindows()
{
    for hwnd in WinGetList("ahk_class SunAwtWindow ahk_exe fiji-windows-x64.exe")
    {
        ; Window Spy identifies the separate Jaunch overlay by this class and
        ; executable. Its title and PID vary, so do not use either. Repeatedly
        ; make it non-topmost, lower it, and hide it without closing a process.
        try WinSetAlwaysOnTop(0, "ahk_id " hwnd)
        try WinMoveBottom("ahk_id " hwnd)
        try WinHide("ahk_id " hwnd)
    }
}

MoveKnownWorkflowWindowsOnce()
{
    for title in ["1 / 2", "2 / 2", "1 / 4", "2 / 4", "3 / 4", "4 / 4"]
    {
        if hwnd := WinExist(title)
        {
            try WinMove(10, 10, , , hwnd)
        }
    }
    MoveFijiToolbarOnce()
    HideFijiLauncherOverlayWindows()
}

StartWorkflowWindowWatch()
{
    global WorkflowWindowWatchDeadline := A_TickCount + 15000
    SetTimer(CatchUpWorkflowWindows, 100)
}

CatchUpWorkflowWindows()
{
    global WorkflowWindowWatchDeadline
    MoveKnownWorkflowWindowsOnce()
    if (A_TickCount >= WorkflowWindowWatchDeadline)
        SetTimer(CatchUpWorkflowWindows, 0)
}

; Position an already-visible Fiji toolbar when this helper starts.
MoveKnownWorkflowWindowsOnce()
StartWorkflowWindowWatch()

; Reuse the original four-point helper's shell-hook behavior: move a placement
; dialog immediately when Windows creates it. Java can assign the final title a
; fraction later, so each creation event also schedules one small delayed retry.
DllCall("RegisterShellHookWindow", "ptr", A_ScriptHwnd)
SHELLHOOK := DllCall("RegisterWindowMessage", "str", "SHELLHOOK")
OnMessage(SHELLHOOK, ShellMessage)

ShellMessage(wParam, lParam, msg, hwnd)
{
    ; HSHELL_WINDOWCREATED = 1
    if (wParam != 1)
        return

    try
        title := WinGetTitle("ahk_id " lParam)
    catch
    {
        title := ""
    }

    if PlacementDialogTitle(title)
    {
        try WinMove(10, 10, , , "ahk_id " lParam)
    }

    ; AWT can create a window before assigning its final title. Re-scan long
    ; enough for delayed dialogs and the separate Jaunch overlay to settle.
    StartWorkflowWindowWatch()
}

AlignmentDialogExists()
{
    for title in [
        "1 / 2", "2 / 2", "Alignment QC", "Full-grid QC",
        "1 / 4", "2 / 4", "3 / 4", "4 / 4",
        "ALL DONE"
    ]
    {
        if WinExist(title)
            return true
    }
    return false
}

; Z is only intercepted while one of the workflow's Fiji dialogs exists.
; It advances either alignment route, accepts QC, and dismisses ALL DONE
; before closing this helper.
#HotIf AlignmentDialogExists()
z::
{
    for title in [
        "1 / 2", "2 / 2", "Alignment QC", "Full-grid QC",
        "1 / 4", "2 / 4", "3 / 4", "4 / 4",
        "ALL DONE"
    ]
    {
        if hwnd := WinExist(title)
        {
            WinActivate(hwnd)
            if WinWaitActive(hwnd, , 0.5)
                Send("{Enter}")
            if title = "ALL DONE"
                ExitApp()
            return
        }
    }
}
#HotIf

; X selects Retry on either QC dialog. Both dialogs default to Accept;
; Down selects Retry, Enter confirms.
#HotIf WinExist("Alignment QC") || WinExist("Full-grid QC")
x::
{
    for title in ["Alignment QC", "Full-grid QC"]
    {
        if hwnd := WinExist(title)
        {
            WinActivate(hwnd)
            if WinWaitActive(hwnd, , 0.5)
                Send("{Down}{Enter}")
            return
        }
    }
}
#HotIf

; Keep the explicit global emergency stop used by the existing helper workflow.
Esc::ExitApp
