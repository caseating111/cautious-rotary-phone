#Requires AutoHotkey v2.0
#SingleInstance Force

SetTitleMatchMode(2)

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

; Reuse the original four-point helper's shell-hook behavior: move a placement
; dialog once when Windows creates it. This does not activate or confirm it.
DllCall("RegisterShellHookWindow", "ptr", A_ScriptHwnd)
SHELLHOOK := DllCall("RegisterWindowMessage", "str", "SHELLHOOK")
OnMessage(SHELLHOOK, ShellMessage)

ShellMessage(wParam, lParam, msg, hwnd)
{
    ; HSHELL_WINDOWCREATED = 1
    if (wParam != 1)
        return

    try title := WinGetTitle("ahk_id " lParam)
    catch
        return

    if PlacementDialogTitle(title)
        try WinMove(10, 10, , , "ahk_id " lParam)
}

; Java dialogs can be created before their final title is visible to the shell
; hook. This tiny fallback only repositions recognised workflow windows.
SetTimer(KeepWorkflowWindowsVisible, 300)

KeepWorkflowWindowsVisible()
{
    for title in ["1 / 2", "2 / 2", "1 / 4", "2 / 4", "3 / 4", "4 / 4"]
    {
        if hwnd := WinExist(title)
            try WinMove(10, 10, , , hwnd)
    }

    ; Keep Fiji's small main toolbar window visible at the upper-right. Do not
    ; touch image windows; only exact main-window titles are considered.
    for title in ["Fiji", "ImageJ"]
    {
        if hwnd := WinExist(title)
        {
            try
            {
                WinGetPos(, , w, h, hwnd)
                MonitorGetWorkArea(1, &left, &top, &right, &bottom)
                x := Max(left, right - w - 10)
                WinMove(x, top + 10, , , hwnd)
            }
            break
        }
    }
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
