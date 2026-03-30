using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System.Collections;

public class CameraController : MonoBehaviour
{
    [Header("References")]
    public Camera mainCamera;
    public Button toggleButton;
    public TextMeshProUGUI buttonLabel;

    [Header("Board Settings")]
    public int boardLength = 20; // Default

    [Header("Transition")]
    public float transitionTime = 1.0f;
    public AnimationCurve moveCurve = AnimationCurve.EaseInOut(0, 0, 1, 1);

    // State
    private bool isTopDown = false; // "2D" state
    private bool isAnimating = false;
    
    // calculated targets
    private Vector3 targetPos3D;
    private Quaternion targetRot3D;
    private Vector3 targetPos2D;
    private Quaternion targetRot2D;

    void Start()
    {
        if (mainCamera == null) mainCamera = Camera.main;

        // 1. Capture/Define Rotations
        targetRot3D = Quaternion.Euler(48.81f, 0, 0); // Hardcoded standard isometric angle
        targetRot2D = Quaternion.Euler(90f, 0f, 0f);

        // 2. Calculate positions based on current boardLength
        RecalculatePositions();

        // 3. Force the camera to the correct start position IMMEDIATELY
        SnapCamera();

        // 4. Hook up button
        if (toggleButton != null)
            toggleButton.onClick.AddListener(ToggleCameraMode);
        
        UpdateLabel();
    }

    public void UpdateBoardSize(int newLength)
    {
        boardLength = newLength;
        RecalculatePositions();

        // If not animating, snap to new position immediately
        if (!isAnimating)
        {
            SnapCamera();
        }
    }

    void RecalculatePositions()
    {
        float center = (boardLength - 1) / 2f;

        // 3D Target: Back up based on board length
        targetPos3D = new Vector3(center, boardLength, -boardLength / 2f);

        // 2D Target: Top down
        targetPos2D = new Vector3(center, boardLength * 1.5f, center);
    }

    void SnapCamera()
    {
        // Instantly sets the camera position/rotation to the current mode's target
        mainCamera.transform.position = isTopDown ? targetPos2D : targetPos3D;
        mainCamera.transform.rotation = isTopDown ? targetRot2D : targetRot3D;
    }

    void ToggleCameraMode()
    {
        if (isAnimating) return;
        StartCoroutine(AnimateCamera(!isTopDown));
    }

    IEnumerator AnimateCamera(bool goTopDown)
    {
        isAnimating = true;
        float timer = 0f;

        Vector3 startPos = mainCamera.transform.position;
        Quaternion startRot = mainCamera.transform.rotation;
        
        Vector3 endPos = goTopDown ? targetPos2D : targetPos3D;
        Quaternion endRot = goTopDown ? targetRot2D : targetRot3D;

        while (timer < transitionTime)
        {
            timer += Time.deltaTime;
            float t = timer / transitionTime;
            float curveT = moveCurve.Evaluate(t);

            mainCamera.transform.position = Vector3.Lerp(startPos, endPos, curveT);
            mainCamera.transform.rotation = Quaternion.Lerp(startRot, endRot, curveT);

            yield return null;
        }

        // Snap to exact values at end of animation
        mainCamera.transform.position = endPos;
        mainCamera.transform.rotation = endRot;

        isTopDown = goTopDown;
        isAnimating = false;
        UpdateLabel();
    }

    void UpdateLabel()
    {
        if (buttonLabel != null)
            buttonLabel.text = isTopDown ? "3D" : "2D";
    }
}