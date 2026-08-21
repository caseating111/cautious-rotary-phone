#Requires AutoHotkey v2.0
#SingleInstance Force

SetTitleMatchMode(2)

AlignmentDialogExists()
{
    for title in [
        "1 / 2", "2 / 2", "Alignment QC",
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
; It advances either the full-column or preserved four-point route, accepts QC,
; and dismisses ALL DONE before closing this helper.
#HotIf AlignmentDialogExists()
z::
{
    for title in [
        "1 / 2", "2 / 2", "Alignment QC",
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

; X is only intercepted while Alignment QC exists on the full-column route.
; The Fiji choice defaults to Accept; Down selects Retry, Enter confirms.
#HotIf WinExist("Alignment QC")
x::
{
    if hwnd := WinExist("Alignment QC")
    {
        WinActivate(hwnd)
        if WinWaitActive(hwnd, , 0.5)
            Send("{Down}{Enter}")
    }
}
#HotIf

; Keep the explicit global emergency stop used by the existing helper workflow.
Esc::ExitApp
