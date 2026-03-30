using System.Collections.Generic;

[System.Serializable]
public class ReplayData
{
    public Config config;
    public List<TurnData> turns;
    public int winner;
    public string win_reason;
    public int total_turns;

    public BotStats bot1_stats;
    public BotStats bot2_stats;
}

[System.Serializable]
public class BotStats
{
    public string name;
}

[System.Serializable]
public class Config
{
    public int grid_width;
    public int grid_height;
}

[System.Serializable]
public class TurnData
{
    public int turn;
    public GameState game_state;
}

[System.Serializable]
public class GameState
{
    public int grid_width;
    public int grid_height;
    public List<Snake> snakes;
    public List<Apple> apples;
    public MapData map; 
}

[System.Serializable]
public class MapData
{
    public List<Point> obstacles;
    
    // --- NEW: V2 Mechanics ---
    public List<Point> shed_walls;
    public List<TreeData> trees;
    // -------------------------
}

// --- NEW: Tree Structure ---
[System.Serializable]
public class TreeData
{
    public int x;
    public int y;
    public string type; // "NORMAL" or "GOLDEN"
}
// ---------------------------

[System.Serializable]
public class Snake
{
    public int id;
    public List<Point> body;
    public bool alive;
    public int score;
    public int length;
    public int energy;
}

[System.Serializable]
public class Apple
{
    public int x;
    public int y;
    public string type;
}

[System.Serializable]
public class Point
{
    public int x;
    public int y;
}