using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class Launcher {
    [STAThread]
    private static void Main() {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string script = Path.Combine(root, "control_center", "control_center.py");
        string python = @"C:\Python314\pythonw.exe";
        try {
            if (!File.Exists(script)) throw new Exception("Keep this launcher beside the control_center folder.");
            if (!File.Exists(python)) throw new Exception("Python 3.14 is required on this laptop.");
            Process.Start(new ProcessStartInfo {
                FileName = python, Arguments = "\"" + script + "\"", WorkingDirectory = root,
                UseShellExecute = false, CreateNoWindow = true
            });
        } catch (Exception error) {
            MessageBox.Show(error.Message, "Enugu Air Control Center", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
