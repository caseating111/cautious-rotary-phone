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

MoveFijiToolbarOnce()
{
    ; Fiji itself is responsible for making its main interface visible. Prefer
    ; the exact title observed on the target desktop; use geometry only as a
    ; compatibility fallback for other Fiji/ImageJ builds.
    bestHwnd := 0

    for title in ["(Fiji Is Just) ImageJ", "ImageJ", "Fiji"]
    {
        if hwnd := WinExist(title)
        {
            try
            {
                className := WinGetClass(hwnd)
                WinGetPos(, , &w, &h, hwnd)
                if (className = "SunAwtFrame" && w >= 250 && h >= 40 && h <= 320)
                {
                    bestHwnd := hwnd
                    break
                }
            }
        }
    }

    if !bestHwnd
    {
        bestWidth := 0
        for hwnd in WinGetList()
        {
            try className := WinGetClass(hwnd)
            catch
                continue
            if (className != "SunAwtFrame")
                continue

            try
            {
                WinGetPos(, , &w, &h, hwnd)
                title := WinGetTitle(hwnd)
            }
            catch
                continue

            ; Image windows are much taller; the main Fiji/ImageJ toolbar is short and wide.
            if (w < 250 || h < 40 || h > 320)
                continue
            if (InStr(title, "1 / 4") || InStr(title, "2 / 4") || InStr(title, "3 / 4") || InStr(title, "4 / 4"))
                continue

            if (w > bestWidth)
            {
                bestHwnd := hwnd
                bestWidth := w
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
}

; Position an already-visible Fiji toolbar when this helper starts.
MoveKnownWorkflowWindowsOnce()

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

    try title := WinGetTitle("ahk_id " lParam)
    catch title := ""

    if PlacementDialogTitle(title)
    {
        try WinMove(10, 10, , , "ahk_id " lParam)
    }

    ; One catch-up pass only: no permanent timer, polling or repeated jitter.
    SetTimer(MoveKnownWorkflowWindowsOnce, -120)
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
