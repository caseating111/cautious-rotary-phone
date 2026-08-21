#Requires AutoHotkey v2.0
#SingleInstance Force

SetTitleMatchMode(2)

; Register for shell window-created events.
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

    ; Only touch the four Fiji calibration dialogs.
    if (
        InStr(title, "1 / 4") ||
        InStr(title, "2 / 4") ||
        InStr(title, "3 / 4") ||
        InStr(title, "4 / 4")
    )
    {
        ; Move ONCE when the dialog is created.
        ; Does not activate or press anything.
        try WinMove(10, 10, , , "ahk_id " lParam)
    }
}


; Z = confirm current Fiji calibration dialog
z::
{
    titles := [
        "1 / 4",
        "2 / 4",
        "3 / 4",
        "4 / 4"
    ]

    for title in titles
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

Esc::ExitApp