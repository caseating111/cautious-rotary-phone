#Requires AutoHotkey v2.0
#SingleInstance Force

SetTitleMatchMode(2)

WorkflowWindowWatchDeadline := 0
WorkflowSourceTitle := ""
DuplicatePromptSource := ""
DuplicatePromptDeadline := 0

PlacementDialogTitle(title)
{
    return InStr(title, "1 / 4") || InStr(title, "2 / 4") || InStr(title, "3 / 4") || InStr(title, "4 / 4")
}

FijiWorkflowDialog(title)
{
    return WinExist(title " ahk_class SunAwtDialog ahk_exe fiji-windows-x64.exe")
}

RememberWorkflowSource(title)
{
    global WorkflowSourceTitle
    if !PlacementDialogTitle(title)
        return
    parts := StrSplit(title, " -- ")
    if (parts.Length >= 3)
        WorkflowSourceTitle := parts[3]
}

ClearFijiOnCancel()
{
    configPath := A_UserProfile "\\.cautious-rotary-phone\\config.json"
    try settings := FileRead(configPath)
    catch
        return true
    return InStr(settings, '"clear_fiji_on_cancel": "0"') = 0
}

ClearCancelledWorkflowWindows()
{
    global WorkflowSourceTitle
    if !ClearFijiOnCancel()
        return
    if preview := WinExist("__alignment_view__ ahk_class SunAwtFrame ahk_exe fiji-windows-x64.exe")
        try WinClose("ahk_id " preview)
    if (WorkflowSourceTitle != "") {
        if source := WinExist(WorkflowSourceTitle " ahk_class SunAwtFrame ahk_exe fiji-windows-x64.exe")
            try WinClose("ahk_id " source)
    }
}

ArmDuplicatePromptCancellation()
{
    global WorkflowSourceTitle, DuplicatePromptSource, DuplicatePromptDeadline
    if (WorkflowSourceTitle = "")
        return
    DuplicatePromptSource := WorkflowSourceTitle
    DuplicatePromptDeadline := A_TickCount + 1800
    SetTimer(CancelDelayedDuplicatePrompt, 80)
}

CancelDelayedDuplicatePrompt()
{
    global DuplicatePromptSource, DuplicatePromptDeadline
    if (A_TickCount >= DuplicatePromptDeadline) {
        SetTimer(CancelDelayedDuplicatePrompt, 0)
        DuplicatePromptSource := ""
        return
    }
    for hwnd in WinGetList("ahk_class SunAwtDialog ahk_exe fiji-windows-x64.exe")
    {
        try title := WinGetTitle(hwnd)
        catch
            continue
        if !PlacementDialogTitle(title)
            continue
        parts := StrSplit(title, " -- ")
        if (parts.Length >= 3 && parts[3] = DuplicatePromptSource) {
            WinActivate(hwnd)
            if WinWaitActive(hwnd, , 0.3)
                Send("{Esc}")
        }
    }
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

DemoteFijiUtilityWindows()
{
    for hwnd in WinGetList("ahk_class SunAwtWindow ahk_exe fiji-windows-x64.exe")
    {
        ; This broad Java utility-window class includes the launcher overlay.
        ; Do not hide or close it: make every member non-topmost and lower it.
        try WinSetAlwaysOnTop(0, "ahk_id " hwnd)
        try WinMoveBottom("ahk_id " hwnd)
    }
}

PinWorkflowDialogs()
{
    for title in ["Next plate", "ROI 1-click", "1 / 4", "2 / 4", "3 / 4", "4 / 4", "Full-grid QC"]
    {
        if hwnd := FijiWorkflowDialog(title)
        {
            try RememberWorkflowSource(WinGetTitle(hwnd))
            try WinMove(10, 10, , , hwnd)
            try WinSetAlwaysOnTop(1, "ahk_id " hwnd)
        }
    }
}

PlaceAlignmentPreviewBelowDialogs()
{
    if !(preview := WinExist("__alignment_view__ ahk_class SunAwtFrame ahk_exe fiji-windows-x64.exe"))
        return

    MonitorGetWorkArea(1, &left, &top, &right, &bottom)
    targetX := left + 10
    ; The next-plate notice precedes the preview, so it does not need to reserve
    ; screen space.  Keep the preview close to the compact click/QC dialogs.
    targetY := top + 230
    for title in ["ROI 1-click", "1 / 4", "2 / 4", "3 / 4", "4 / 4", "Full-grid QC"]
    {
        if dialog := FijiWorkflowDialog(title)
        {
            try
            {
                WinGetPos(&dialogX, &dialogY, &dialogW, &dialogH, dialog)
                targetY := Max(targetY, dialogY + dialogH + 12)
            }
        }
    }
    try WinMove(targetX, targetY, , , preview)
}

MoveKnownWorkflowWindowsOnce()
{
    PinWorkflowDialogs()
    PlaceAlignmentPreviewBelowDialogs()
    MoveFijiToolbarOnce()
    DemoteFijiUtilityWindows()
}

StartWorkflowWindowWatch()
{
    global WorkflowWindowWatchDeadline := A_TickCount + 10000
    SetTimer(CatchUpWorkflowWindows, 100)
}

CatchUpWorkflowWindows()
{
    global WorkflowWindowWatchDeadline
    MoveKnownWorkflowWindowsOnce()
    if (A_TickCount >= WorkflowWindowWatchDeadline)
        SetTimer(CatchUpWorkflowWindows, 0)
}

; Java assigns some titles after creation, so position immediately and keep the
; bounded watcher for delayed title assignment and the launcher overlay.
DllCall("RegisterShellHookWindow", "ptr", A_ScriptHwnd)
SHELLHOOK := DllCall("RegisterWindowMessage", "str", "SHELLHOOK")
OnMessage(SHELLHOOK, ShellMessage)

ShellMessage(wParam, lParam, msg, hwnd)
{
    if (wParam != 1)
        return
    try title := WinGetTitle("ahk_id " lParam)
    catch
        title := ""
    if PlacementDialogTitle(title) && WinExist("ahk_id " lParam " ahk_class SunAwtDialog ahk_exe fiji-windows-x64.exe")
    {
        try RememberWorkflowSource(title)
        try WinMove(10, 10, , , "ahk_id " lParam)
    }
    StartWorkflowWindowWatch()
}

; Position an already-visible Fiji toolbar when this helper starts.
MoveKnownWorkflowWindowsOnce()
StartWorkflowWindowWatch()

AlignmentDialogExists()
{
    for title in [
        "Next plate", "ROI 1-click", "1 / 2", "2 / 2", "Alignment QC", "Full-grid QC",
        "1 / 4", "2 / 4", "3 / 4", "4 / 4",
        "ALL DONE"
    ]
    {
        if FijiWorkflowDialog(title)
            return true
    }
    return false
}

; Z is only intercepted while one of the workflow's Fiji dialogs exists.
; It advances either alignment route, accepts QC, and dismisses ALL DONE.
; The controller owns this helper for its entire session so it also handles a
; delayed stale Fiji macro window if one appears after completion.
#HotIf AlignmentDialogExists()
z::
{
    for title in [
        "Next plate", "ROI 1-click", "1 / 2", "2 / 2", "Alignment QC", "Full-grid QC",
        "1 / 4", "2 / 4", "3 / 4", "4 / 4",
        "ALL DONE"
    ]
    {
        if hwnd := FijiWorkflowDialog(title)
        {
            WinActivate(hwnd)
            if WinWaitActive(hwnd, , 0.5)
                Send("{Enter}")
            if title = "ALL DONE"
                ArmDuplicatePromptCancellation()
            return
        }
    }
}
#HotIf

; C cancels the active Fiji workflow dialog. ImageJ's native wait-for-user and
; GenericDialog implementations treat Escape as Cancel and abort the macro.
#HotIf AlignmentDialogExists()
c::
{
    for title in [
        "Next plate", "ROI 1-click", "1 / 2", "2 / 2", "Alignment QC", "Full-grid QC",
        "1 / 4", "2 / 4", "3 / 4", "4 / 4", "ALL DONE"
    ]
    {
        if hwnd := FijiWorkflowDialog(title)
        {
            WinActivate(hwnd)
            if WinWaitActive(hwnd, , 0.5)
                Send("{Esc}")
            ArmDuplicatePromptCancellation()
            SetTimer(ClearCancelledWorkflowWindows, -250)
            return
        }
    }
}
#HotIf

; X selects Retry on either QC dialog. Both dialogs default to Accept;
; Down selects Retry, Enter confirms.
#HotIf FijiWorkflowDialog("Alignment QC") || FijiWorkflowDialog("Full-grid QC")
x::
{
    for title in ["Alignment QC", "Full-grid QC"]
    {
        if hwnd := FijiWorkflowDialog(title)
        {
            WinActivate(hwnd)
            if WinWaitActive(hwnd, , 0.5)
                Send("{Home}{Down}{Enter}")
            return
        }
    }
}
#HotIf

; Keep the explicit global emergency stop used by the existing helper workflow.
Esc::ExitApp
