using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System.IO;
using System.Collections.Generic;

public class FileManager : MonoBehaviour
{
    [Header("References")]
    public ReplayManager replayManager;
    public TMP_Dropdown fileDropdown;

    private string replayFolderPath;
    private List<string> foundFiles = new List<string>();
    
    // Auto-detection variables
    private FileSystemWatcher fileWatcher;
    private bool needsRefresh = false;

    void Start()
    {
        SetupReplayFolder();
        RefreshFileList();
        SetupFileWatcher();

        if (fileDropdown != null)
        {
            fileDropdown.onValueChanged.AddListener(OnFileSelected);
        }
    }

    void Update()
    {
        // FileWatcher runs on a background thread. 
        // We use this flag to update the UI on the main Unity thread.
        if (needsRefresh)
        {
            needsRefresh = false;
            RefreshFileList();
        }
    }

    void OnDestroy()
    {
        if (fileWatcher != null) fileWatcher.Dispose();
    }

    void SetupReplayFolder()
    {
#if UNITY_EDITOR
        // In Editor: Project_Root/Replays
        replayFolderPath = Path.Combine(Application.dataPath, "../Assets/Replays");
#else
        string path = Application.dataPath;

        // MAC FIX: Step out of the .app bundle
        if (Application.platform == RuntimePlatform.OSXPlayer)
        {
            // Path is: Game.app/Contents/Resources/Data
            // Parent 1: Resources
            // Parent 2: Contents
            // Parent 3: Game.app
            // Parent 4: The folder CONTAINING the game
            path = Directory.GetParent(path).Parent.Parent.Parent.FullName;
        }
        // WINDOWS/LINUX: Step out of the _Data folder
        else if (Application.platform == RuntimePlatform.WindowsPlayer || Application.platform == RuntimePlatform.LinuxPlayer)
        {
            // Path is: Game_Data
            // Parent 1: The folder CONTAINING the game
            path = Directory.GetParent(path).FullName;
        }

        replayFolderPath = Path.Combine(path, "Replays");
#endif

        // Create the folder immediately if it doesn't exist
        if (!Directory.Exists(replayFolderPath))
        {
            Directory.CreateDirectory(replayFolderPath);
            Debug.Log("Created Replay Folder at: " + replayFolderPath);
        }
    }

    void SetupFileWatcher()
    {
        // Watch for any changes to .json files in that folder
        fileWatcher = new FileSystemWatcher(replayFolderPath, "*.json");
        fileWatcher.NotifyFilter = NotifyFilters.FileName | NotifyFilters.LastWrite | NotifyFilters.CreationTime;

        // Listen for creation and deletion
        fileWatcher.Created += OnFileChanged;
        fileWatcher.Deleted += OnFileChanged;
        
        // Start watching
        fileWatcher.EnableRaisingEvents = true;
    }

    private void OnFileChanged(object sender, FileSystemEventArgs e)
    {
        // Flag for the Update loop
        needsRefresh = true;
    }

    public void RefreshFileList()
    {
        if (fileDropdown == null) return;
        
        // Save current selection to restore it if possible
        string currentSelection = "";
        if (fileDropdown.options.Count > 0 && fileDropdown.value < foundFiles.Count)
        {
            currentSelection = Path.GetFileName(foundFiles[fileDropdown.value]);
        }

        foundFiles.Clear();
        fileDropdown.ClearOptions();

        if (Directory.Exists(replayFolderPath))
        {
            string[] files = Directory.GetFiles(replayFolderPath, "*.json");
            List<string> options = new List<string>();

            int targetIndex = 0;

            for (int i = 0; i < files.Length; i++)
            {
                foundFiles.Add(files[i]);
                string fileName = Path.GetFileName(files[i]);
                options.Add(fileName);

                // If this file matches what we had selected, mark its index
                if (fileName == currentSelection) targetIndex = i;
            }

            fileDropdown.AddOptions(options);
            
            // Restore selection without triggering the event again
            fileDropdown.SetValueWithoutNotify(targetIndex);

            // If we have files but nothing is loaded yet, load the first one
            // (Optional: remove if you prefer the empty state)
            if (foundFiles.Count > 0 && string.IsNullOrEmpty(currentSelection))
            {
                 LoadFileAtIndex(0);
            }
        }
    }

    void OnFileSelected(int index)
    {
        LoadFileAtIndex(index);
    }

    void LoadFileAtIndex(int index)
    {
        if (index >= 0 && index < foundFiles.Count)
        {
            if (File.Exists(foundFiles[index]))
            {
                string jsonContent = File.ReadAllText(foundFiles[index]);
                replayManager.InitializeGame(jsonContent);
            }
        }
    }
}