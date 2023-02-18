import sqlite3
import datetime
import wx
import wx.grid

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Agenda", size=(600, 400))
        panel = MainPanel(self)
        self.Show()

class MainPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.tasks = {}
        self.create_grid()
        save_button = wx.Button(self, label="Enregistrer")
        save_button.Bind(wx.EVT_BUTTON, self.on_save_button)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.grid, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
        hbox.Add(save_button, flag=wx.ALL, border=5)
        self.SetSizer(hbox)
        self.current_hour = None
        self.current_minute = None

        task_string = input("Entrez les tâches séparées par des virgules: ")
        start_hour = int(input("Entrez l'heure de départ (0 à 23): "))
        tasks = self.parse_tasks(task_string, start_hour)
        print(tasks)
        # Remplir la grille avec les tâches
        for task in tasks:
            hour = task['time']
            row = hour
            col = 1
            task_text = task['task']
            self.grid.SetCellValue(row, col, task_text)

    def create_grid(self):
        # Creer la grille pour afficher l'agenda
        self.grid = wx.grid.Grid(self)
        self.grid.CreateGrid(24, 3)
        self.grid.SetColLabelValue(0, "Heure")
        self.grid.SetColLabelValue(1, "Tâche")
        self.grid.AutoSizeColumns()

        for i in range(24):
            hour = datetime.time(i, 0, 0)
            self.grid.SetCellValue(i, 0, hour.strftime('%H:%M'))
            self.grid.SetReadOnly(i, 0, True)
            self.grid.SetCellAlignment(i, 0, wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            event_id = wx.NewIdRef()
            self.grid.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.on_cell_left_double_click, id=event_id)
            btn = wx.ToggleButton(self.grid, label="Valider")
            self.grid.SetCellEditor(i, 2, wx.grid.GridCellBoolEditor())
            self.grid.SetCellRenderer(i, 2, wx.grid.GridCellBoolRenderer())


    def parse_tasks(self, task_string, start_hour):
        # Initialiser la liste de tâches et l'heure de départ
        tasks = []
        hour, minute = divmod(start_hour, 60)
        # Séparer les tâches à partir de la chaîne de caractères
        task_list = task_string.split(',')

        # Parcourir les tâches et les ajouter à la liste avec leur heure respective
        for i,task in enumerate(task_list):
            tasks.append({'time': start_hour+i, 'task': task.strip()})


        # Retourner le dictionnaire de tâches
        return tasks

    def on_cell_left_double_click(self, event):
        row, col = event.GetRow(), event.GetCol()

        if col == 1:
            hour_str = self.grid.GetCellValue(row, 0)
            self.current_hour, self.current_minute = map(int, hour_str.split(":"))
            dialog = wx.TextEntryDialog(self, "Entrez la tâche à faire pour %02d:%02d :" % (
            self.current_hour, self.current_minute))
            if dialog.ShowModal() == wx.ID_OK:
                task = dialog.GetValue()
                self.tasks[datetime.time(self.current_hour, self.current_minute)] = {'task': task, 'validated': False}
                self.grid.SetCellValue(row, col, task)
                self.grid.SetCellValue(row, col + 1, 'Non')
                print("Tâche ajoutee :", task)
            dialog.Destroy()

        elif col == 2:
            task = self.grid.GetCellValue(row, col - 1)
            if task:
                validated = self.grid.GetCellValue(row, col)
                hour = datetime.time(self.current_hour, self.current_minute)
                if validated == "Oui":
                    self.grid.SetCellValue(row, col, "Non")
                    self.tasks[hour]['validated'] = False
                else:
                    self.grid.SetCellValue(row, col, "Oui")
                    self.tasks[hour]['validated'] = True

    def on_save_button(self, event):
        # Ouvrir la connexion à la base de données
        conn = sqlite3.connect('tasks.db')
        conn.row_factory = sqlite3.Row

        # Creer la table "journee" s'il n'existe pas dejà
        conn.execute('''CREATE TABLE IF NOT EXISTS journee
                                    (id INTEGER PRIMARY KEY,
                                     date DATE)''')

        # Creer la table "task" s'il n'existe pas dejà
        conn.execute('''CREATE TABLE IF NOT EXISTS task
                                    (id INTEGER PRIMARY KEY,
                                     heure TIME,
                                     tache TEXT,
                                     is_validated INTEGER,
                                     journee_id INTEGER,
                                     FOREIGN KEY (journee_id) REFERENCES journee(id))''')

        try:
            c = conn.cursor()
            # Vérifier si la journée existe dans la table "journée"
            date_str = datetime.datetime.now().strftime('%Y-%m-%d')
            c.execute('SELECT id FROM journee WHERE date = ?', (date_str,))
            row = c.fetchone()

            # Si la journée n'existe pas, l'ajouter à la table "journée"
            if not row:
                c.execute('INSERT INTO journee (date) VALUES (?)', (date_str,))
                journee_id = c.lastrowid
            else:
                journee_id = row[0]

            # Parcourir les cellules de la grille et enregistrer les tâches dans la base de données
            for row in range(self.grid.GetNumberRows()):
                time_str = self.grid.GetCellValue(row, 0)
                task_str = self.grid.GetCellValue(row, 1)
                is_validated_str = self.grid.GetCellValue(row, 2)
                if task_str:
                    c.execute('SELECT id FROM task WHERE heure = ? AND journee_id = ?', (time_str, journee_id))
                    row = c.fetchone()

                    if row:
                        # La tâche existe déjà, effectuer une mise à jour
                        task_id = row[0]
                        c.execute('UPDATE task SET tache = ?, is_validated = ? WHERE id = ?', (task_str, is_validated_str, task_id))
                    else:
                        # La tâche n'existe pas, l'ajouter
                        c.execute('INSERT INTO task (heure, tache, is_validated, journee_id) VALUES (?, ?, ?, ?)',
                                  (time_str, task_str,is_validated_str, journee_id))
                    print("Tâche enregistrée :", task_str)

            # Fermer la connexion à la base de données
            conn.commit()
            conn.close()

        except sqlite3.Error as e:
            print("Error: ", e.args[0])
            conn.rollback()
            conn.close()


app = wx.App()
frame = MainFrame()
frame.Show()
app.MainLoop()

