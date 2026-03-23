' NexusTrader Silent Launcher
' Double-click this file to start both servers without any flash.
' It runs NexusTrader.bat in the background and the two server
' windows will open on their own.

Dim shell
Set shell = CreateObject("WScript.Shell")

' Get folder this VBS lives in
Dim folder
folder = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Run the bat file (0 = hidden window for launcher, servers open their own windows)
shell.Run Chr(34) & folder & "\NexusTrader.bat" & Chr(34), 1, False

Set shell = Nothing
