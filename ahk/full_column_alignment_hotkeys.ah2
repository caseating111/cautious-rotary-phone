#Requires AutoHotkey v2.0
#SingleInstance Force

SetTitleMatchMode(2)

; Z = accept/advance the current Fiji alignment dialog.
z::
{
    for title in ["1 / 2", "2 / 2", "Alignment QC"]
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

; X = Retry from the Alignment QC dialog.
; The Fiji choice defaults to Accept; Down selects Retry, Enter confirms.
x::
{
    if hwnd := WinExist("Alignment QC")
    {
        WinActivate(hwnd)
        if WinWaitActive(hwnd, , 0.5)
            Send("{Down}{Enter}")
    }
}

Esc::ExitApp
