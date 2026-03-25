' Lanceur Windows : evite les raccourcis .lnk vers .bat / cmd (erreurs "acces au chemin" sur certaines machines).
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = base
sh.Run "cmd.exe /c run.bat", 1, False
