#Requires AutoHotkey v2.0
#SingleInstance Force

SetTitleMatchMode(2)

AlignmentDialogExists()
{
    for title in ["Next plate", "1 / 2", "2 / 2", "Alignment QC"]
    {
        if WinExist(title)
            return true
    }
    return false
}

; Z is only intercepted while one of the workflow's Fiji dialogs exists.
; It acknowledges Next plate, advances first/last-column placement, and accepts QC.
#HotIf AlignmentDialogExists()
z::
{
    for title in ["Next plate", "1 / 2", "2 / 2", "Alignment QC"]
    {
        if hwnd := WinExist(title)
        {
            WinActivate(hwnd)
            if WinWaitActive(hwnd, , 0.5)
                Send("{Enter}")
            return
        }
    }
}
#HotIf

; X is only intercepted while Alignment QC exists.
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
