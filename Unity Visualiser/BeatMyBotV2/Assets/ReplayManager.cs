using UnityEngine;
using UnityEngine.UI; 
using TMPro;          
using System.Collections.Generic;

public class ReplayManager : MonoBehaviour
{
    [Header("Replay Settings")]
    public TextAsset jsonFile;
    [Range(0.01f, 2.0f)]
    public float replaySpeed = 0.5f;

    [Header("Camera Control")] 
    public CameraController camController;

    [Header("Board Settings")]
    public GameObject floorTilePrefab; 
    public GameObject wallPrefab;      

    // --- NEW: V2 Prefabs ---
    [Header("Tree & Shed Prefabs")]
    public GameObject normalTreePrefab;
    public GameObject goldenTreePrefab;
    public GameObject shedWallPrefab;
    // -----------------------

    [Header("Snake Prefabs")]
    public GameObject player1Prefab;
    public GameObject player2Prefab;

    [Header("Apple Prefabs")]
    public GameObject applePrefab;
    public GameObject gapplePrefab;
    public GameObject spapplePrefab;
    public GameObject stapplePrefab;
    public GameObject papplePrefab;

    [Header("UI References")]
    public Button btnPrev;
    public Button btnNext;
    public Button btnPause; 
    public Button btnRestart;
    public Slider speedSlider; 
    public TextMeshProUGUI pauseButtonText;
    public TextMeshProUGUI winnerText;
    
    [Header("Stats UI")]
    public TextMeshProUGUI p1NameText;   
    public TextMeshProUGUI p2NameText;   
    public TextMeshProUGUI p1LengthText; 
    public TextMeshProUGUI p2LengthText;
    public TextMeshProUGUI p1EnergyText; 
    public TextMeshProUGUI p2EnergyText; 
    
    private ReplayData replayData;
    private float timer;
    private int currentTurnIndex = 0;
    private bool isPaused = false;
    private GameObject[,] gridObjects;
    private CellType[,] currentGridTypes;
    private int width, height;
    private List<GameObject> floorTiles = new List<GameObject>();
    private Image pauseButtonImage;

    // --- UPDATED: Added new Enum types for trees and shed walls ---
    private enum CellType { Empty, Snake1, Snake2, Wall, AppleNormal, AppleGod, AppleSpeed, AppleStun, ApplePoison, TreeNormal, TreeGolden, ShedWall }

    void Start()
    {
        if (btnNext != null) btnNext.onClick.AddListener(NextTurn);
        if (btnPrev != null) btnPrev.onClick.AddListener(PrevTurn);
        if (btnPause != null) 
        {
            btnPause.onClick.AddListener(TogglePause);
            pauseButtonImage = btnPause.GetComponent<Image>();
        }
        if (btnRestart != null) btnRestart.onClick.AddListener(RestartReplay);

        if (speedSlider != null)
        {
            speedSlider.value = replaySpeed; 
            speedSlider.onValueChanged.AddListener(SetReplaySpeed);
        }

        if (jsonFile != null)
        {
            InitializeGame();
        }
    }

    void Update()
    {
        if (replayData == null || isPaused || currentTurnIndex >= replayData.turns.Count - 1) return;

        timer += Time.deltaTime;

        if (timer >= replaySpeed)
        {
            timer = 0;
            currentTurnIndex++;
            RenderTurn(currentTurnIndex);
        }
    }

    public void SetReplaySpeed(float speed)
    {
        if (speed <= 0) speed = 0.001f;
        replaySpeed = 1/speed;
    }

    public void InitializeGame(string jsonOverride = null)
    {
        if (gridObjects != null) foreach (var obj in gridObjects) if (obj != null) Destroy(obj);

        string jsonToUse = !string.IsNullOrEmpty(jsonOverride) ? jsonOverride : (jsonFile != null ? jsonFile.text : "");

        if (string.IsNullOrEmpty(jsonToUse)) return;

        replayData = JsonUtility.FromJson<ReplayData>(jsonToUse);
        
        width = replayData.config.grid_width;
        height = replayData.config.grid_height;

        if (camController != null) 
        {
            camController.UpdateBoardSize(width);
        }

        GenerateBoard();

        if (replayData.bot1_stats != null && p1NameText != null) 
            p1NameText.text = replayData.bot1_stats.name;
        
        if (replayData.bot2_stats != null && p2NameText != null) 
            p2NameText.text = replayData.bot2_stats.name;

        gridObjects = new GameObject[width, height];
        currentGridTypes = new CellType[width, height];
        
        currentTurnIndex = 0;
        
        if (winnerText != null) winnerText.gameObject.SetActive(false);

        RenderTurn(0);
        
        SetPause(false); 
    }

    public void TogglePause()
    {
        SetPause(!isPaused);
    }

    public void SetPause(bool shouldPause)
    {
        isPaused = shouldPause;
        
        if (pauseButtonText != null) 
            pauseButtonText.text = isPaused ? "4" : ";";

        if (pauseButtonImage != null)
        {
            pauseButtonImage.color = isPaused ? Color.red : Color.white; 
        }
    }

    public void NextTurn()
    {
        SetPause(true); 
        if (currentTurnIndex < replayData.turns.Count - 1)
        {
            currentTurnIndex++;
            RenderTurn(currentTurnIndex);
        }
    }

    public void PrevTurn()
    {
        SetPause(true);
        if (currentTurnIndex > 0)
        {
            currentTurnIndex--;
            RenderTurn(currentTurnIndex);
        }
    }

    public void RestartReplay()
    {
        currentTurnIndex = 0;
        if (winnerText != null) winnerText.gameObject.SetActive(false); 
        RenderTurn(0);
        SetPause(false); 
    }

    void GenerateBoard()
    {
        foreach (GameObject tile in floorTiles) if (tile != null) Destroy(tile);
        floorTiles.Clear();

        if (floorTilePrefab == null) return;

        for (int x = 0; x < width; x++)
        {
            for (int y = 0; y < height; y++)
            {
                Vector3 pos = new Vector3(x, -5f, y);
                GameObject tile = Instantiate(floorTilePrefab, pos, Quaternion.identity, transform);
                floorTiles.Add(tile);
            }
        }
    }

    void RenderTurn(int turnIndex)
    {
        TurnData turn = replayData.turns[turnIndex];
        GameState state = turn.game_state;
        CellType[,] targetGrid = new CellType[width, height];

        if (winnerText != null)
        {
            if (turnIndex >= replayData.turns.Count - 1)
            {
                winnerText.text = replayData.win_reason;
                winnerText.gameObject.SetActive(true);
            }
            else
            {
                winnerText.gameObject.SetActive(false);
            }
        }

        UpdateStatsUI(state);

        // Map base objects (rendered before snakes and apples)
        List<Point> obstacles = GetObstacles(state); 
        foreach (var obs in obstacles) if (IsValid(obs.x, obs.y)) targetGrid[obs.x, obs.y] = CellType.Wall;

        // --- NEW: Map Trees and Shed Walls ---
        if (state.map != null && state.map.shed_walls != null)
        {
            foreach (var shed in state.map.shed_walls) if (IsValid(shed.x, shed.y)) targetGrid[shed.x, shed.y] = CellType.ShedWall;
        }

        if (state.map != null && state.map.trees != null)
        {
            foreach (var tree in state.map.trees)
            {
                if (IsValid(tree.x, tree.y)) 
                {
                    targetGrid[tree.x, tree.y] = (tree.type == "GOLDEN") ? CellType.TreeGolden : CellType.TreeNormal;
                }
            }
        }
        // -------------------------------------

        foreach (var apple in state.apples) if (IsValid(apple.x, apple.y)) targetGrid[apple.x, apple.y] = GetAppleType(apple.type);
        if (state.snakes.Count > 0 && state.snakes[0].alive) foreach (var part in state.snakes[0].body) if (IsValid(part.x, part.y)) targetGrid[part.x, part.y] = CellType.Snake1;
        if (state.snakes.Count > 1 && state.snakes[1].alive) foreach (var part in state.snakes[1].body) if (IsValid(part.x, part.y)) targetGrid[part.x, part.y] = CellType.Snake2;

        // Instantiate differences
        for (int x = 0; x < width; x++)
        {
            for (int y = 0; y < height; y++)
            {
                if (targetGrid[x, y] != currentGridTypes[x, y]) UpdateCell(x, y, targetGrid[x, y]);
            }
        }
    }

    void UpdateStatsUI(GameState state)
    {
        if (state.snakes.Count > 0)
        {
            if (p1LengthText != null) p1LengthText.text = "Len: " + state.snakes[0].length;
            if (p1EnergyText != null) p1EnergyText.text = "Eng: " + state.snakes[0].energy;
        }
        else
        {
             if (p1LengthText != null) p1LengthText.text = "Dead";
             if (p1EnergyText != null) p1EnergyText.text = "-";
        }

        if (state.snakes.Count > 1)
        {
            if (p2LengthText != null) p2LengthText.text = "Len: " + state.snakes[1].length;
            if (p2EnergyText != null) p2EnergyText.text = "Eng: " + state.snakes[1].energy;
        }
        else
        {
             if (p2LengthText != null) p2LengthText.text = "Dead";
             if (p2EnergyText != null) p2EnergyText.text = "-";
        }
    }

    void UpdateCell(int x, int y, CellType newType)
    {
        if (gridObjects[x, y] != null) { Destroy(gridObjects[x, y]); gridObjects[x, y] = null; }
        GameObject prefabToSpawn = null;
        float altitude = 0f;

        switch (newType)
        {
            case CellType.Snake1: prefabToSpawn = player1Prefab; altitude = 0.5f; break;
            case CellType.Snake2: prefabToSpawn = player2Prefab; altitude = 0.5f; break;
            case CellType.Wall:   prefabToSpawn = wallPrefab;    altitude = 0.5f; break; 
            
            // --- NEW: Setting new prefabs ---
            case CellType.TreeNormal: prefabToSpawn = normalTreePrefab; altitude = 0f; break;
            case CellType.TreeGolden: prefabToSpawn = goldenTreePrefab; altitude = 0f; break;
            case CellType.ShedWall:   prefabToSpawn = shedWallPrefab;   altitude = 0.5f; break;
            // --------------------------------

            case CellType.AppleNormal: prefabToSpawn = applePrefab; break;
            case CellType.AppleGod:    prefabToSpawn = gapplePrefab; break;
            case CellType.AppleSpeed:  prefabToSpawn = spapplePrefab; break;
            case CellType.AppleStun:   prefabToSpawn = stapplePrefab; break;
            case CellType.ApplePoison: prefabToSpawn = papplePrefab; break;
        }

        if (prefabToSpawn != null)
        {
            Vector3 pos = new Vector3(x, altitude, y); 
            gridObjects[x, y] = Instantiate(prefabToSpawn, pos, prefabToSpawn.transform.rotation, transform);
        }
        currentGridTypes[x, y] = newType;
    }

    bool IsValid(int x, int y) { return x >= 0 && x < width && y >= 0 && y < height; }

    CellType GetAppleType(string typeString)
    {
        switch (typeString)
        {
            case "GOD": return CellType.AppleGod;
            case "SPEED": return CellType.AppleSpeed;
            case "SLEEP": return CellType.AppleStun;
            case "POISON": return CellType.ApplePoison;
            default: return CellType.AppleNormal;
        }
    }

    List<Point> cachedObstacles;
    List<Point> GetObstacles(GameState state)
    {
        if (state.map != null && state.map.obstacles != null) return state.map.obstacles;
        return new List<Point>();
    }
}