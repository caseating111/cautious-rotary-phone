#Requires AutoHotkey v2.0
#SingleInstance Force

if (A_Args.Length < 3)
    ExitApp

launcher := A_Args[1]
controllerPid := Integer(A_Args[2])
launcherPid := Integer(A_Args[3])

while ProcessExist(controllerPid)
    Sleep(50)

if ProcessExist(launcherPid)
    RunWait(A_ComSpec " /c taskkill /PID " launcherPid " /T /F", , "Hide")

deadline := A_TickCount + 5000
while ProcessExist(launcherPid) && A_TickCount < deadline
    Sleep(50)

Sleep(300)
Run('"' launcher '"')
ExitApp
