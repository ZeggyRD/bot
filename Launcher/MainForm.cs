using System;
using System.Diagnostics;
using System.Drawing;
using System.Windows.Forms;

namespace OTWLauncher
{
    public class MainForm : Form
    {
        public MainForm()
        {
            this.Text = "OTW Music System";
            this.Size = new Size(400, 300);
            this.BackColor = Color.FromArgb(18, 18, 18);
            this.StartPosition = FormStartPosition.CenterScreen;

            Font titleFont = new Font("Arial", 16, FontStyle.Bold);
            Font buttonFont = new Font("Segoe UI", 10, FontStyle.Bold);

            Label title = new Label();
            title.Text = "🚀 OTW Launcher";
            title.ForeColor = Color.White;
            title.Font = titleFont;
            title.Location = new Point(100, 20);
            title.AutoSize = true;

            Button btnAutoBot = new Button();
            btnAutoBot.Text = "Abrir AutoBot";
            btnAutoBot.Font = buttonFont;
            btnAutoBot.Size = new Size(200, 35);
            btnAutoBot.Location = new Point(100, 70);
            btnAutoBot.BackColor = Color.FromArgb(30, 215, 96);
            btnAutoBot.Click += (s, e) => Process.Start("C:\\Users\\ceram\\Music\\OTW_MUSIC_SYSTEM\\AutoBot\\AutoBot.exe");

            Button btnMarketing = new Button();
            btnMarketing.Text = "Abrir Marketing System";
            btnMarketing.Font = buttonFont;
            btnMarketing.Size = new Size(200, 35);
            btnMarketing.Location = new Point(100, 115);
            btnMarketing.BackColor = Color.FromArgb(30, 215, 96);
            btnMarketing.Click += (s, e) => Process.Start("C:\\Users\\ceram\\Music\\OTW_MUSIC_SYSTEM\\MarketingSystem\\MarketingSystem.exe");

            Button btnVisualizer = new Button();
            btnVisualizer.Text = "Abrir Visual Creator";
            btnVisualizer.Font = buttonFont;
            btnVisualizer.Size = new Size(200, 35);
            btnVisualizer.Location = new Point(100, 160);
            btnVisualizer.BackColor = Color.FromArgb(30, 215, 96);
            btnVisualizer.Click += (s, e) => Process.Start("C:\\Users\\ceram\\Music\\OTW_MUSIC_SYSTEM\\VisualizerCreator\\VisualizerCreator.exe");

            this.Controls.Add(title);
            this.Controls.Add(btnAutoBot);
            this.Controls.Add(btnMarketing);
            this.Controls.Add(btnVisualizer);
        }
    }
}
